# Code-first spec demo (toy example)

*The C# code is the contract source, and the OpenAPI spec is a reviewed snapshot.*

This is the companion to `kiota-contract-demo`. That demo was **contract-first**: someone hand-copied
the YAML into C#, and nothing checked the copy (its "Experiment 2" broke clients silently).
This demo flips the direction: the gateway's C# code **produces** the OpenAPI spec, the spec is
committed as a snapshot, and CI gates every change against it.

```
 kiota-contract-demo (contract-first)      code-first-spec-demo (this one)
 ────────────────────────────────────      ─────────────────────────────────────
 YAML ──hand-copy──► gateway C#            gateway C# ──export──► JSON snapshot
 YAML ──Kiota──────► client                JSON snapshot ──Kiota──► client
 gap: is the C# faithful? (unchecked)      gate: oasdiff + drift check in CI
```

## The workflow

```
  developer edits gateway C#
          │
          ▼
  ./scripts/export-spec.sh ──► contracts/studies-v1.json ─┐  commit code + snapshot
          │                    contracts/studies-v2.json  │  TOGETHER, so reviewers
          │                                               │  see the API diff in the PR
          ▼                                               ▼
  PR CI: ./scripts/api-gate.sh                       client repo:
    1. export a fresh spec from the PR's code          ./scripts/generate-clients.sh
    2. BREAKING?  committed → fresh   (oasdiff)        (Kiota, from the committed JSON;
    3. DRIFT?     committed ≠ fresh   (cmp)             never needs the gateway source)
```

Release versions and contract versions are still separate numbers:

| Artifact    | Version | Where it is defined                                   |
|-------------|---------|-------------------------------------------------------|
| Contract v1 | 1.1.0   | `OpenApiSetup.V1ContractVersion` (a C# constant now)  |
| Contract v2 | 2.0.0   | `OpenApiSetup.V2ContractVersion`                      |
| Gateway     | 3.1.0   | `gateway/Gateway.csproj`                              |
| Client      | 2.1.0   | `client/ClientApp.csproj`                             |

## Quick start

Prerequisites: **.NET 10 SDK** and **oasdiff** ([install](https://github.com/oasdiff/oasdiff#installation)).

```zsh
./scripts/run-demo.sh              # build both, start gateway, run client, stop gateway
./scripts/api-gate.sh              # the CI gate on the current code  → ✔ No API change
./scripts/try-breaking-change.sh   # replays the rename from the first demo → ✘ caught
```

To browse the API, run `dotnet run --project gateway` and open <http://localhost:5080/swagger>.
Swagger UI renders the documents the gateway generates from its own code
(`/openapi/v1.json` and `/openapi/v2.json`, chosen from the dropdown). Unlike the
contract-first demo, the page cannot disagree with the code. Compare it with the
committed `contracts/` snapshot to see a pending API change.

## The gate has three outcomes

| Result | Meaning                                         | What to do                                            |
|--------|-------------------------------------------------|-------------------------------------------------------|
| ✔      | Code produces exactly the committed spec        | Nothing                                               |
| ⚠      | Compatible change, but `contracts/` is stale    | Bump the MINOR, run `export-spec.sh`, commit snapshot |
| ✘      | Breaking change vs the committed spec           | Revert, or ship it as a new major (`/api/v3`)         |

The ⚠ case fails CI on purpose. An API change nobody reviewed is the real risk, even when it's compatible.

`try-breaking-change.sh` renames `PatientName → FullName` in the v1 DTO (the "harmless refactor"
from the first demo's Experiment 2), runs the gate, then restores the file:

```
✎ "Harmless refactor": PatientName → FullName in the v1 DTO

▶ v1: committed snapshot → spec exported from current code
error  [response-required-property-removed] in API GET /api/v1/studies
       removed the required property `items/patientName` from the response with the `200` status
error  [response-required-property-removed] in API GET /api/v1/studies/{id}
       removed the required property `patientName` from the response with the `200` status
  ✘ BREAKING change in v1. Revert it, or ship it as a new major (/api/v3 + a new document).
▶ v2: committed snapshot → spec exported from current code
  ✔ No API change.

→ Caught before merge. In the first demo the same rename shipped and blanked out patient names.
```

## Where the contract lives in the code

In code-first, **wire-format decisions are code**, so they must be deliberate. Each one below
shows up in the generated spec:

| Contract fact                         | Code that produces it                                              |
|---------------------------------------|--------------------------------------------------------------------|
| Field names and types                 | DTO records `StudyV1`, `StudyV2`, `PatientV2`                      |
| `required` vs optional                | Constructor parameter **without** vs **with** a default value      |
| …which needs                          | `RespectRequiredConstructorParameters = true` (Program.cs)         |
| Enums as `"CT"`, not `0`              | `JsonStringEnumConverter` (Program.cs)                             |
| Response types visible to the spec    | `TypedResults.Ok(...)` and `Results<Ok<T>, ProblemHttpResult>`     |
| `404 → application/problem+json`      | `.ProducesProblem(StatusCodes.Status404NotFound)`                  |
| One document per major                | `AddOpenApi("v1")`, `AddOpenApi("v2")` + `.WithGroupName(...)`     |
| `info.version`                        | `OpenApiSetup.V1ContractVersion` / `V2ContractVersion`             |
| Snapshot independent of host/port     | Document transformer clears `servers`                              |

## Code-first gotchas (all found while building this demo)

1. **`Results.Ok(x)` hides the type.** The generator only sees `IResult`. Use `TypedResults`.
2. **Without `JsonStringEnumConverter`** enums appear as integers in both the wire and the spec.
3. **Without `RespectRequiredConstructorParameters`** nothing is `required`, and oasdiff then
   reports a removed property as optional-removed (a much weaker signal).
4. **Nullable enums (`Priority?`) in OpenAPI 3.1** become `enum: [..., null]`, and Kiota turns
   that `null` into a junk enum member (`openapi-json-null-sentinel-value-…`). The v1 DTO uses
   a default value (`Priority Priority = Priority.Routine`) instead: optional, never null.
   *This is the general lesson of code-first: read the generated spec in every PR, because
   that's where generator quirks surface.*
5. **The `servers` block records the host the spec was exported from**, so the snapshot would
   drift between machines. It's cleared, which is why Kiota warns "no server url". That's
   expected, because the client sets `BaseUrl` itself.

## Experiments to try

**1. A compatible change.** Add `string? AccessionNumber = null` to `StudyV2` and run
`./scripts/api-gate.sh`. You should get ⚠, not ✘. Then follow the full loop: bump
`V2ContractVersion` to `2.1.0`, run `./scripts/export-spec.sh`, review the JSON diff, run
`./scripts/generate-clients.sh`, and the client gains a typed `AccessionNumber` property.

**2. Direction matters.** Compatibility rules are asymmetric. For **responses**, the server may
promise *more* (add fields, make optional → required) but never less. For **requests**, it's
the reverse: the server may accept *more* but never demand more. Try removing the default from
`Priority` in `StudyV1` and see what the gate says.

**3. Trace a domain change.** Rename a value in `Domain/Study.cs` (for example `Modality.MG`)
and run the gate. The DTOs reuse the domain enums, so the change leaks into **both** contracts.
That's the shortcut this toy takes, and the gate is what makes it visible.

## Alternative: export at build time instead of at runtime

`export-spec.sh` starts the gateway and downloads `/openapi/*.json`. That's simple and has no
build magic. ASP.NET Core can also write the documents on every `dotnet build` with the
`Microsoft.Extensions.ApiDescription.Server` package and an `<OpenApiDocumentsDirectory>`
property in the csproj. Same idea, earlier feedback. It isn't wired into this demo, so check
the generated file names against the scripts if you switch.

## Left out on purpose

- **The real baseline.** In CI, compare against `contracts/` on the target branch or the last
  release tag (`git show v3.1.0:contracts/studies-v1.json`), not the working copy.
- **Behavior.** Schemas can't say "returns 404, not an empty 200". Add integration tests
  (`WebApplicationFactory`) or consumer-driven contract tests (**PactNet**) for that.
- **Delivering `contracts/` to the client repo**, for example a GitHub Release asset pinned by tag.

## Tested with

.NET SDK 10.0 · Microsoft.AspNetCore.OpenApi 10.0.10 (OpenAPI 3.1 output) · Kiota 1.36.1 ·
Microsoft.Kiota.Bundle 2.1.2 · oasdiff 1.34.0
