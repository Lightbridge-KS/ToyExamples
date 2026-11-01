using Gateway.Api;
using Gateway.Domain;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.FileProviders;

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

// Swagger UI renders the contract YAML files themselves (not docs generated from code),
// so what you read in the browser is exactly what the clients were generated from.
app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new PhysicalFileProvider(Path.Combine(AppContext.BaseDirectory, "contracts")),
    RequestPath = "/contracts",
    ContentTypeProvider = new FileExtensionContentTypeProvider
    {
        Mappings = { [".yaml"] = "application/yaml" }
    }
});
app.UseSwaggerUI(ui =>
{
    ui.SwaggerEndpoint("/contracts/studies-api.v2.0.0.yaml", "v2 · contract 2.0.0 (current)");
    ui.SwaggerEndpoint("/contracts/studies-api.v1.1.0.yaml", "v1 · contract 1.1.0 (deprecated)");
});

app.MapGet("/", () => "Studies Gateway 3.0.0 — contracts: v1.1.0 (/api/v1, deprecated), v2.0.0 (/api/v2) — docs: /swagger");
app.MapStudiesV1();
app.MapStudiesV2();

app.Run("http://localhost:5080");
