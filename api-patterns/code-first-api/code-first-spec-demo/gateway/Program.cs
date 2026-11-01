using System.Text.Json.Serialization;
using Gateway.Api;
using Gateway.Domain;

// ─────────────────────────────────────────────────────────────────────
//  Studies Gateway — release 3.1.0   (CODE-FIRST)
//
//  The C# code is the source of truth. The OpenAPI documents are
//  GENERATED from it and committed to contracts/ as a reviewed snapshot:
//
//    GET /openapi/v1.json   → contracts/studies-v1.json   (contract 1.1.0)
//    GET /openapi/v2.json   → contracts/studies-v2.json   (contract 2.0.0)
// ─────────────────────────────────────────────────────────────────────

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<StudyRepository>();
builder.Services.AddProblemDetails();

// Wire-format decisions are now CODE, so they show up in the generated spec.
builder.Services.ConfigureHttpJsonOptions(o =>
{
    o.SerializerOptions.Converters.Add(new JsonStringEnumConverter());   // "CT", not 0
    o.SerializerOptions.RespectRequiredConstructorParameters = true;      // ctor params → "required"
});

builder.Services.AddStudiesOpenApi();

var app = builder.Build();

app.MapOpenApi();   // serves /openapi/{documentName}.json

// Swagger UI renders the documents GENERATED from this code, so the page always shows
// what the running gateway really exposes (and what export-spec.sh will snapshot).
app.UseSwaggerUI(ui =>
{
    ui.SwaggerEndpoint("/openapi/v2.json", $"v2 · contract {OpenApiSetup.V2ContractVersion} (current)");
    ui.SwaggerEndpoint("/openapi/v1.json", $"v1 · contract {OpenApiSetup.V1ContractVersion}");
});

app.MapGet("/", () => "Studies Gateway 3.1.0 (code-first) — specs at /openapi/v1.json, /openapi/v2.json — docs: /swagger")
   .ExcludeFromDescription();
app.MapStudiesV1();
app.MapStudiesV2();

app.Run("http://localhost:5080");
