using Gateway.Domain;

namespace Gateway.Api;

/// <summary>
/// Implements contract <c>contracts/studies-api.v2.0.0.yaml</c> on <c>/api/v2</c>.
/// </summary>
public static class V2Endpoints
{
    // Wire format of contract v2.0.0.
    private sealed record PatientV2(string Hn, string Name);
    private sealed record StudyV2(string Id, PatientV2 Patient, string Modality, string Priority);

    public static void MapStudiesV2(this IEndpointRouteBuilder app)
    {
        var v2 = app.MapGroup("/api/v2");

        v2.MapGet("/studies", (StudyRepository repo) =>
            repo.All().Select(ToV2));

        v2.MapGet("/studies/{id}", (string id, StudyRepository repo) =>
            repo.Find(id) is { } study
                ? Results.Ok(ToV2(study))
                : Results.Problem(statusCode: 404, title: "Study not found", detail: $"No study with id '{id}'."));
    }

    private static StudyV2 ToV2(Study s) => new(
        Id:       s.Id,
        Patient:  new PatientV2(s.Patient.Hn, s.Patient.Name),
        Modality: s.Modality.ToString(),
        Priority: s.Priority.ToString().ToLowerInvariant());
}
