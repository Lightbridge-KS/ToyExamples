using System.Text.Json;
using System.Text.Json.Serialization;
using ClientApp.Generated.StudiesV1;
using ClientApp.Generated.StudiesV2;
using Microsoft.Kiota.Abstractions;
using Microsoft.Kiota.Abstractions.Authentication;
using Microsoft.Kiota.Bundle;
using Microsoft.Kiota.Http.HttpClientLibrary.Middleware.Options;
using V2 = ClientApp.Generated.StudiesV2.Models;

// ─────────────────────────────────────────────────────────────────────
//  Client App — one process, two "releases", so you can see both at once:
//
//    ACT 1  client 1.4.0  built against contract v1.0.0  (Generated/StudiesV1)
//    ACT 2  client 2.0.0  built against contract v2.0.0  (Generated/StudiesV2)
//    ACT 3  contrast: a hand-written strict client (no Kiota)
//
//  Both generated clients talk to the SAME gateway release (3.0.0).
// ─────────────────────────────────────────────────────────────────────

var gatewayUrl = Environment.GetEnvironmentVariable("GATEWAY_URL") ?? "http://localhost:5080";

// A request adapter = HttpClient + middleware + (de)serializers.
// The generated client is only a thin, typed facade over it.
IRequestAdapter NewAdapter() =>
    new DefaultRequestAdapter(new AnonymousAuthenticationProvider()) { BaseUrl = gatewayUrl };


// ── ACT 1 ─────────────────────────────────────────────────────────────
Header("ACT 1 · Client 1.4.0 (contract v1.0.0)  →  Gateway 3.0.0 (/api/v1 = contract v1.1.0)");

var v1Client = new StudiesV1Client(NewAdapter());
var headers  = new HeadersInspectionHandlerOption { InspectResponseHeaders = true };

var oldStudies = await v1Client.Api.V1.Studies.GetAsync(cfg => cfg.Options.Add(headers)) ?? [];

foreach (var s in oldStudies)
{
    // Tolerant reader #1: `priority` was added in 1.1.0. This client has no typed
    // property for it, so Kiota parks it in AdditionalData instead of failing.
    var extra = s.AdditionalData.TryGetValue("priority", out var p) ? $"AdditionalData[priority]={p}" : "";

    // Tolerant reader #2: `MG` was added in 1.1.0. Unknown enum value → null, not an exception.
    var modality = s.Modality?.ToString() ?? "<unknown>";

    Console.WriteLine($"  {s.Id}  {s.PatientName,-16}  {modality,-9}  {extra}");
}

// Runtime signal: the gateway tells this old client that v1 is on its way out.
if (headers.ResponseHeaders.TryGetValue("Sunset", out var sunset))
    Console.WriteLine($"  ⚠ Server says v1 is deprecated. Sunset: {sunset.First()} → plan the move to v2.");


// ── ACT 2 ─────────────────────────────────────────────────────────────
Header("ACT 2 · Client 2.0.0 (contract v2.0.0)  →  Gateway 3.0.0 (/api/v2 = contract v2.0.0)");

var v2Client = new StudiesV2Client(NewAdapter());

foreach (var s in await v2Client.Api.V2.Studies.GetAsync() ?? [])
    Console.WriteLine($"  {s.Id}  HN {s.Patient?.Hn}  {s.Patient?.Name,-16}  {s.Modality,-3}  {s.Priority}");

// Typed errors: the contract declares `404 → Problem`, so Kiota throws a typed exception.
try
{
    await v2Client.Api.V2.Studies["S-999"].GetAsync();
}
catch (V2.Problem problem)
{
    Console.WriteLine($"  404 caught as typed V2.Problem → \"{problem.Title}\": {problem.Detail}");
}


// ── ACT 3 ─────────────────────────────────────────────────────────────
Header("ACT 3 · Contrast: hand-written STRICT client (enum frozen at v1.0.0), same response");

using var http = new HttpClient { BaseAddress = new Uri(gatewayUrl) };
var json = await http.GetStringAsync("/api/v1/studies/S-003");
Console.WriteLine($"  raw JSON: {json}");

try
{
    var strictJson = new JsonSerializerOptions(JsonSerializerDefaults.Web) { Converters = { new JsonStringEnumConverter() } };
    var study = JsonSerializer.Deserialize<StrictStudy>(json, strictJson);
    Console.WriteLine($"  parsed: {study}");
}
catch (JsonException ex)
{
    Console.WriteLine($"  💥 {ex.Message.Split(" | ")[0]}");
    Console.WriteLine("     A strict reader breaks on an ADDITIVE change. The generated Kiota client did not.");
}

Console.WriteLine();


// ── helpers ───────────────────────────────────────────────────────────
static void Header(string title) =>
    Console.WriteLine($"\n── {title} {new string('─', Math.Max(3, 96 - title.Length))}");

/// <summary>What a typical hand-written DTO looks like: enum values frozen at the time it was written.</summary>
enum StrictModality { CT, MR, US, XR }
record StrictStudy(string Id, string PatientName, StrictModality Modality);
