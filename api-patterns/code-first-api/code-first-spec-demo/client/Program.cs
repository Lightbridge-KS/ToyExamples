using ClientApp.Generated.StudiesV1;
using ClientApp.Generated.StudiesV2;
using Microsoft.Kiota.Abstractions;
using Microsoft.Kiota.Abstractions.Authentication;
using Microsoft.Kiota.Bundle;
using V2 = ClientApp.Generated.StudiesV2.Models;

// ─────────────────────────────────────────────────────────────────────
//  Client App — the end of the code-first chain:
//
//    gateway C#  ──export-spec.sh──►  contracts/*.json  ──Kiota──►  this client
//
//  The client repo only ever needs the committed contracts/, never the
//  gateway source. It cannot tell (and does not care) that the spec was
//  generated from code rather than written by hand.
// ─────────────────────────────────────────────────────────────────────

var gatewayUrl = Environment.GetEnvironmentVariable("GATEWAY_URL") ?? "http://localhost:5080";

IRequestAdapter NewAdapter() =>
    new DefaultRequestAdapter(new AnonymousAuthenticationProvider()) { BaseUrl = gatewayUrl };


Header("v1 · contract 1.1.0 · /api/v1");
var v1 = new StudiesV1Client(NewAdapter());

foreach (var s in await v1.Api.V1.Studies.GetAsync() ?? [])
    Console.WriteLine($"  {s.Id}  {s.PatientName,-16}  {s.Modality,-3}  {s.Priority}");


Header("v2 · contract 2.0.0 · /api/v2");
var v2 = new StudiesV2Client(NewAdapter());

foreach (var s in await v2.Api.V2.Studies.GetAsync() ?? [])
    Console.WriteLine($"  {s.Id}  HN {s.Patient?.Hn}  {s.Patient?.Name,-16}  {s.Modality,-3}  {s.Priority}");

// .ProducesProblem(404) in the gateway code → 404 in the spec → typed exception here.
try
{
    await v2.Api.V2.Studies["S-999"].GetAsync();
}
catch (V2.ProblemDetails problem)
{
    Console.WriteLine($"  404 caught as typed ProblemDetails → \"{problem.Title}\": {problem.Detail}");
}

Console.WriteLine();

static void Header(string title) =>
    Console.WriteLine($"\n── {title} {new string('─', Math.Max(3, 64 - title.Length))}");
