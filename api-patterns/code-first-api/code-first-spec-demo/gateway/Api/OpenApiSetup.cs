using Microsoft.AspNetCore.OpenApi;

namespace Gateway.Api;

/// <summary>
/// One OpenAPI document per MAJOR contract version.
/// In code-first, the contract version is a constant you bump in code:
///   additive change  → bump MINOR here
///   breaking change  → don't: add a new document (v3) and a new /api/v3 group
/// </summary>
public static class OpenApiSetup
{
    public const string V1ContractVersion = "1.1.0";
    public const string V2ContractVersion = "2.0.0";

    public static IServiceCollection AddStudiesOpenApi(this IServiceCollection services)
    {
        // Endpoints are assigned to a document by .WithGroupName("v1") / ("v2").
        services.AddOpenApi("v1", options => Configure(options, V1ContractVersion));
        services.AddOpenApi("v2", options => Configure(options, V2ContractVersion));
        return services;
    }

    private static void Configure(OpenApiOptions options, string contractVersion) =>
        options.AddDocumentTransformer((document, _, _) =>
        {
            document.Info.Title   = "Studies API";
            document.Info.Version = contractVersion;
            document.Servers?.Clear();   // keep the snapshot independent of the host/port it was exported from
            return Task.CompletedTask;
        });
}
