# Kiota contract demo (toy example)

*Keeping two C# repos compatible across versions with one OpenAPI contract.*

A toy example of **contract-first API evolution**. An API Gateway and a Client App
release independently, and they stay compatible because both depend on a third thing,
the **OpenAPI contract**, rather than on each other.

```
              contracts/  (single source of truth)
   ┌──────────────────────────────────────────────────┐
   │  v1.0.0 ──► v1.1.0 ──► v1.2.0 ✘ (rejected by CI) │
   │                                                  │
   │  v2.0.0  (breaking → new major, new path)        │
   └───────┬───────────────────────────┬──────────────┘
           │ implements                │ generates (Kiota)
           ▼                           ▼
   ┌───────────────────┐      ┌─────────────────────────┐
   │ Gateway 3.0.0     │◄─────│ Client 1.4.0 (v1.0.0)   │  /api/v1
   │  /api/v1 = 1.1.0  │      │ Client 2.0.0 (v2.0.0)   │  /api/v2
   │  /api/v2 = 2.0.0  │◄─────│                         │
   └───────────────────┘      └─────────────────────────┘
```

> In real life `contracts/`, `gateway/` and `client/` are three repos (or the contract
> lives in the gateway repo and is published as a release artifact). They share one
> folder here so you can run everything at once.

## The version map

The most important idea is that **release versions and contract versions are different numbers.**

| Artifact     | Version | Meaning                                                     |
|--------------|---------|-------------------------------------------------------------|
| Contract v1  | 1.1.0   | `/api/v1`, deprecated, sunset 2027-06-30                    |
| Contract v2  | 2.0.0   | `/api/v2`, current                                          |
| Gateway      | 3.0.0   | Serves contract 1.1.0 **and** 2.0.0 side by side            |
| Client (old) | 1.4.0   | Built against contract **1.0.0**, still in the field        |
| Client (new) | 2.0.0   | Built against contract 2.0.0                                |

Semantic versioning applies to the **contract**:

```
PATCH  docs/examples only           → nothing to do
MINOR  additive (new optional field, new endpoint, new enum value*)
                                    → old clients keep working, no regeneration needed
MAJOR  breaking (rename/remove, type change, optional→required)
                                    → new file + new /api/vN path, old one kept alive
* only because our policy declares enums OPEN — see "The CI gate" below
```

## Quick start

Prerequisites: **.NET 10 SDK**. Optionally **oasdiff** for the CI gate
([install](https://github.com/oasdiff/oasdiff#installation)).

```zsh
./scripts/run-demo.sh          # build both, start gateway, run client, stop gateway
./scripts/check-breaking.sh    # the contract CI gate (needs oasdiff)
```

Or run them by hand in two terminals:

```zsh
dotnet run --project gateway   # terminal 1 → http://localhost:5080
dotnet run --project client    # terminal 2
```

With the gateway running, open <http://localhost:5080/swagger> for Swagger UI. It renders
the contract YAML files themselves (`contracts/studies-api.v1.1.0.yaml` and
`studies-api.v2.0.0.yaml`, chosen from the dropdown), not docs generated from the gateway
code. So the page shows what the clients were built from, and "Try it out" shows what the
gateway actually returns.

## What you will see

```
── ACT 1 · Client 1.4.0 (contract v1.0.0) → Gateway 3.0.0 (/api/v1 = contract v1.1.0)
  S-001  Somchai Jaidee    CT         AdditionalData[priority]=stat
  S-002  Malee Srisuk      MR         AdditionalData[priority]=routine
  S-003  Wanida Thongdee   <unknown>  AdditionalData[priority]=routine
  ⚠ Server says v1 is deprecated. Sunset: Wed, 30 Jun 2027 23:59:59 GMT → plan the move to v2.

── ACT 2 · Client 2.0.0 (contract v2.0.0) → Gateway 3.0.0 (/api/v2 = contract v2.0.0)
  S-001  HN 6512345  Somchai Jaidee    CT   Stat
  S-002  HN 6598765  Malee Srisuk      MR   Routine
  S-003  HN 6600001  Wanida Thongdee   MG   Routine
  404 caught as typed V2.Problem → "Study not found": No study with id 'S-999'.

── ACT 3 · Contrast: hand-written STRICT client (enum frozen at v1.0.0), same response
  raw JSON: {"id":"S-003","patientName":"Wanida Thongdee","modality":"MG","priority":"routine"}
  💥 The JSON value could not be converted to StrictStudy. Path: $.modality
     A strict reader breaks on an ADDITIVE change. The generated Kiota client did not.
```

**ACT 1 is the point of the whole demo.** A client compiled against contract 1.0.0
talks to a gateway that has moved on to 1.1.0, and nothing breaks:

- `priority` didn't exist in 1.0.0, so there's no typed property for it. Kiota models
  implement `IAdditionalDataHolder`, so the unknown field lands in `AdditionalData`
  instead of being dropped or throwing.
- `MG` didn't exist in 1.0.0. Kiota maps an unknown enum value to `null`
  (enums are generated as `Modality?`) instead of throwing.
- The gateway also sends `Deprecation`, `Sunset` and `Link: rel="successor-version"`
  headers. The old client reads them with `HeadersInspectionHandlerOption`. This is
  the runtime half of the compatibility story.

**ACT 3** is the same JSON read by a typical hand-written DTO with `JsonStringEnumConverter`.
It crashes on an *additive* change. That's why the **Tolerant Reader** behavior matters.

## The CI gate — `scripts/check-breaking.sh`

```
Case 1: v1.0.0 → v1.1.0            ✔ compatible (2 warnings: new enum value)
Case 2: v1.1.0 → v1.2.0 (rename)   ✘ BREAKING: response-required-property-removed
```

By default oasdiff reports a new response enum value as an **error**, because strict
readers (ACT 3) crash on it. This demo makes an explicit, written-down decision instead
of silently ignoring the rule:

1. Every enum in the contracts says in its `description` that it is an **open set**.
2. `contracts/oasdiff-severity.txt` downgrades that one rule to a warning.
3. All consumers are Kiota-generated tolerant readers (proven in ACT 1).

If you can't guarantee point 3 (for example, a third-party consumer), delete the
policy file and treat new enum values as breaking.

## Regenerating the clients — `scripts/generate-clients.sh`

```zsh
dotnet tool restore              # installs Kiota 1.36.1 pinned in .config/dotnet-tools.json
./scripts/generate-clients.sh
```

Two things are pinned so generation is reproducible: the **contract file** (which API
version you build against) and the **generator version**. Each output folder has a
`kiota-lock.json` recording both, plus a hash of the contract. Commit the generated
code; the diff in a pull request then shows exactly how the API surface changed for
this client.

## Experiments to try

**1. Upgrade the old client to v1.1.0.** In `generate-clients.sh`, point StudiesV1 at
`studies-api.v1.1.0.yaml` and regenerate. `Study.Priority` becomes a typed property,
`MG` becomes a known enum value, and the `AdditionalData` column in ACT 1 goes empty.
That's a minor upgrade: regenerate, no code changes required.

**2. Break the gateway without touching the contract.** In `gateway/Api/V1Endpoints.cs`,
rename `PatientName` to `FullName` in the `StudyV1` record and rerun. ACT 1 now
prints a blank patient name, with **no error anywhere**. This exposes the gap in this
toy: nothing proves the gateway actually matches the YAML. See "Left out" below.

**3. Try to sneak a break past CI.** Copy `studies-api.v1.1.0.yaml`, make
`priority` required or remove an endpoint, then run
`./scripts/check-breaking.sh contracts/studies-api.v1.1.0.yaml <your-file>`.

## Key ideas → where to look

| Idea                                       | File                                          |
|--------------------------------------------|-----------------------------------------------|
| Contract is the source of truth            | `contracts/*.yaml`                            |
| Internal model ≠ wire format               | `gateway/Domain/Study.cs`                     |
| Gateway as version adapter (v1 kept alive) | `gateway/Api/V1Endpoints.cs`                  |
| Deprecation / Sunset headers               | `V1Endpoints.AddDeprecationHeaders`           |
| Typed client from a pinned contract        | `client/Generated/*/kiota-lock.json`          |
| Tolerant reader in practice                | `client/Program.cs` ACT 1                     |
| Typed errors from the contract (`404`)     | `client/Program.cs` ACT 2                     |
| Breaking-change gate + written policy      | `scripts/check-breaking.sh`, `oasdiff-severity.txt` |

## Left out on purpose (next steps)

- **Proving the gateway conforms to the contract.** Experiment 2 shows the gap. Options:
  an integration test that runs the generated Kiota client against the gateway
  (`WebApplicationFactory`), a schema-validation test of real responses against the
  YAML, or consumer-driven contract tests with **PactNet** + `can-i-deploy`.
- **`Asp.Versioning`**: plain `MapGroup("/api/v1")` is enough to show the idea.
- **Publishing the contract** as a versioned artifact (GitHub Release, NuGet content
  package, or a contracts repo) that the client repo pins by tag.
- **Auth, a real proxy (YARP), DI registration of the Kiota client** — unrelated to the mechanism.

## Tested with

.NET SDK 10.0 · Kiota 1.36.1 · Microsoft.Kiota.Bundle 2.1.2 · oasdiff 1.34.0
