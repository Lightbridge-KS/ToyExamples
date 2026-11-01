using Gateway.Api;
using Gateway.Domain;

// ─────────────────────────────────────────────────────────────────────
//  Studies Gateway — release 3.0.0
//
//  Serves TWO major contract versions side by side:
//    /api/v1  → contracts/studies-api.v1.1.0.yaml   (deprecated, sunset 2027-06-30)
//    /api/v2  → contracts/studies-api.v2.0.0.yaml   (current)
//
//  The gateway's release number (3.0.0) and the contract numbers
//  (1.1.0, 2.0.0) are deliberately unrelated.
// ─────────────────────────────────────────────────────────────────────

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<StudyRepository>();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.MapGet("/", () => "Studies Gateway 3.0.0 — contracts: v1.1.0 (/api/v1, deprecated), v2.0.0 (/api/v2)");
app.MapStudiesV1();
app.MapStudiesV2();

app.Run("http://localhost:5080");
