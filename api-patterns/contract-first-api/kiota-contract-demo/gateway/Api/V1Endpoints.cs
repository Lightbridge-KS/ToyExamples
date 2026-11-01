using Gateway.Domain;

namespace Gateway.Api;

/// <summary>
/// Implements contract <c>contracts/studies-api.v1.1.0.yaml</c> on <c>/api/v1</c>.
///
/// v1 is an ADAPTER over the internal model: the gateway keeps old clients
/// alive by translating the latest shape down to the v1 wire format.
/// </summary>
public static class V1Endpoints
{
    // Wire format of contract v1.1.0. Field names here ARE the contract.
    private sealed record StudyV1(string Id, string PatientName, string Modality, string Priority);

    // Deprecation policy: announced when v2 shipped, removed after the sunset date.
    private static readonly DateTimeOffset DeprecatedSince = new(2026, 11, 1, 0, 0, 0, TimeSpan.Zero);
    private static readonly DateTimeOffset SunsetOn        = new(2027, 6, 30, 23, 59, 59, TimeSpan.Zero);

    public static void MapStudiesV1(this IEndpointRouteBuilder app)
    {
        var v1 = app.MapGroup("/api/v1")
                    .AddEndpointFilter(AddDeprecationHeaders);

        v1.MapGet("/studies", (StudyRepository repo) =>
            repo.All().Select(ToV1));

        v1.MapGet("/studies/{id}", (string id, StudyRepository repo) =>
            repo.Find(id) is { } study
                ? Results.Ok(ToV1(study))
                : Results.Problem(statusCode: 404, title: "Study not found", detail: $"No study with id '{id}'."));
    }

    private static StudyV1 ToV1(Study s) => new(
        Id:          s.Id,
        PatientName: s.Patient.Name,                       // v2 split this into patient{hn,name}
        Modality:    s.Modality.ToString(),
        Priority:    s.Priority.ToString().ToLowerInvariant());

    /// <summary>Runtime signal to clients: "v1 still works, but plan your move".</summary>
    private static ValueTask<object?> AddDeprecationHeaders(
        EndpointFilterInvocationContext ctx, EndpointFilterDelegate next)
    {
        var headers = ctx.HttpContext.Response.Headers;
        headers["Deprecation"] = $"@{DeprecatedSince.ToUnixTimeSeconds()}";      // RFC 9745
        headers["Sunset"]      = SunsetOn.ToString("R");                          // RFC 8594
        headers.Link           = "</api/v2/studies>; rel=\"successor-version\"";  // RFC 5829
        return next(ctx);
    }
}
