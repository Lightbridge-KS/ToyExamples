// ─────────────────────────────────────────────────────────────────────────────
// THE RECEIVING SIDE (only C-MOVE needs this).
// One long-lived listener for the whole app + a router that hands each
// incoming instance to whichever C-MOVE asked for it.
// ─────────────────────────────────────────────────────────────────────────────
using System.Collections.Concurrent;
using ToyRetrieve.Domain;
using ToyRetrieve.Simulated;

namespace ToyRetrieve.Receiving;

/// <summary>
/// MEDIATOR: matches each incoming C-STORE to the C-MOVE that caused it,
/// using the Move Originator Message ID (0000,1031).
/// </summary>
public sealed class MoveRouter
{
    private readonly ConcurrentDictionary<int, IInstanceSink> _pending = new();

    /// <summary>
    /// Register BEFORE sending the C-MOVE: the first C-STORE can arrive
    /// before the C-MOVE call returns. Dispose the handle to unregister.
    /// </summary>
    public IDisposable Register(int messageId, IInstanceSink sink)
    {
        _pending[messageId] = sink;
        return new Registration(() => _pending.TryRemove(messageId, out _));
    }

    public Task RouteAsync(CStoreRequest request, CancellationToken ct = default)
    {
        if (_pending.TryGetValue(request.MoveOriginatorMessageId, out var sink))
            return sink.OnInstanceAsync(request.Instance, ct);

        // Late arrival after a timeout, or a push nobody asked for.
        Console.WriteLine($"    [Router] orphan {request.Instance.SopInstanceUid}: no pending move, dropped");
        return Task.CompletedTask;
    }

    private sealed class Registration(Action onDispose) : IDisposable
    {
        public void Dispose() => onDispose();
    }
}

/// <summary>
/// The long-lived listener. In real life: a fo-dicom DicomServer whose
/// service implements IDicomCStoreProvider, started once at app startup.
/// It knows nothing about studies or sinks; it just forwards to the router.
/// </summary>
public sealed class StoreScp(MoveRouter router) : ICStoreListener
{
    public Task OnCStoreAsync(CStoreRequest request)
    {
        Console.WriteLine($"    [StoreScp] C-STORE in: {request.Instance.SopInstanceUid} (moveMsgId={request.MoveOriginatorMessageId})");
        return router.RouteAsync(request);
    }
}
