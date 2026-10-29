# DICOM retrieve (toy example)

*C-GET vs C-MOVE behind one Strategy, in ~300 lines of C# with no NuGet packages.*

The smallest program that shows **how to hide two very different DICOM retrieve
protocols behind one interface**, without the difference leaking to callers.

No fo-dicom, no network, no PACS: `Simulated/FakePacs.cs` stands in for all of
that so the *mechanism* is the only thing left to read.

## The idea

```
            caller: RetrieveAsync(studyUid, sink)
                          │
                 IStudyRetriever            ◀── Strategy (the port)
                  ▲        ▲        ▲
                  │        │        └── FallbackRetriever  ◀── Decorator
                  │        │              (C-GET, else C-MOVE)
          CGetRetriever  CMoveRetriever
             │              │  1. router.Register(msgId, sink)
             │              │  2. pacs.CMove(dest = "RAMAAI")
             │              ▼
             │           PACS ──C-STORE (new association)──▶ StoreScp
             │                                                  │
             │                                    MoveRouter ◀──┘ ◀── Mediator
             │                                    (msgId → sink)
             ▼                                        │
           sink  ◀────────────────────────────────────┘
```

The asymmetry (one association vs two, pull vs push) lives entirely *inside*
`CMoveRetriever` + `Receiving/`. The caller only ever sees "study in, instances
into my sink, result out".

## Files

| File | Role | Pattern |
|---|---|---|
| `Domain/Contracts.cs` | What the app needs, in its own words | **Strategy** interface / port |
| `Retrievers/CGetRetriever.cs` | Pull: instances arrive on our association | Strategy #1 (adapter) |
| `Retrievers/CMoveRetriever.cs` | Push: register, ask, wait | Strategy #2 (adapter) |
| `Retrievers/FallbackRetriever.cs` | Try C-GET, fall back to C-MOVE | **Decorator** |
| `Receiving/StoreScp.cs` | Long-lived listener + correlation | **Mediator** (`MoveRouter`) |
| `Simulated/FakePacs.cs` | Stub of the PACS + network | (the outside world) |
| `Program.cs` | Wiring + 4 demos + caller code | **Factory** (composition root) |

## Run

```bash
dotnet run        # .NET 8+ SDK, no NuGet packages needed
```

Demo 4 is the interesting one: two C-MOVEs in flight share **one** listener,
the C-STOREs interleave, and the router still delivers each to the right sink:

```
=== 4. Two C-MOVEs at once on PACS-B ===
  [PACS-B] C-MOVE 1.2.3.100 (msgId=3): dialing 'RAMAAI' on a NEW association
  [PACS-B] C-MOVE 1.2.3.200 (msgId=4): dialing 'RAMAAI' on a NEW association
    [StoreScp] C-STORE in: 1.2.3.200.1 (moveMsgId=4)
      [Sink 1.2.3.200] got 1.2.3.200.1 ✓
    [StoreScp] C-STORE in: 1.2.3.100.1 (moveMsgId=3)
      [Sink 1.2.3.100] got 1.2.3.100.1 ✓
    ...
```

## Toy → real fo-dicom

| Toy | fo-dicom / real world |
|---|---|
| `FakePacs.CGetAsync(uid, callback)` | `DicomCGetRequest` sent via `IDicomClient`; the callback is `client.OnCStoreRequest`. Also add SCP-role storage contexts to `client.AdditionalPresentationContexts`, or the PACS can't send anything back. |
| `FakePacs.CMoveAsync(uid, dest, id)` | `DicomCMoveRequest(destinationAe, studyUid)`; final counts arrive in `OnResponseReceived` (`DicomCMoveResponse`). |
| `StoreScp` | `DicomServerFactory.Create<T>(port)`, where `T : DicomService, IDicomServiceProvider, IDicomCStoreProvider`. Start it at app startup, *before* any move. |
| `CStoreRequest.MoveOriginatorMessageId` | Tag **(0000,1031)** in the incoming C-STORE command set. |
| `_lastMessageId` counter | The C-MOVE request's own `MessageID`. |
| `RegisterMoveDestination(ae, scp)` | The PACS admin adding "AE `RAMAAI` = your-ip:port" to the PACS config. |

## Real-world details the toy skips

- **Message IDs are 16-bit and only unique per association.** Key the router on
  (calling AE of the incoming association, message ID), not message ID alone.
- **Some PACS leave (0000,1031) empty.** Fall back to matching on StudyInstanceUID.
- **Add a timeout.** C-STOREs that arrive after you gave up hit the router's
  "orphan" branch; decide whether to drop them or file them somewhere.
- **C-MOVE needs an inbound port open on your machine; C-GET doesn't.** That
  firewall fact is often the real reason to prefer C-GET when the PACS allows it.

## Try it

1. **The litmus test.** Add `WadoRsRetriever` (DICOMweb) with a fake HTTP
   server. If `Retrieve(...)` in `Program.cs` needs no change, the abstraction
   is right: it describes the *intent*, not the *protocol*.
2. **Another decorator.** Write `TimingRetriever` that wraps any retriever with
   a `Stopwatch`. Notice that no existing class changes (Open/Closed).
3. **See an orphan.** Make `CMoveRetriever` stop waiting after a short timeout
   while the PACS keeps pushing, and watch the router's dropped-instance line.
