using Gateway.Domain;
using Microsoft.AspNetCore.Http.HttpResults;

namespace Gateway.Api;

/// <summary>Contract v2 on <c>/api/v2</c>. Breaking changes vs v1 live here, not in v1.</summary>
public static class V2Endpoints
{
    /// <summary>Wire format of contract v2.</summary>
    public sealed record PatientV2(string Hn, string Name);
    public sealed record StudyV2(string Id, PatientV2 Patient, Modality Modality, Priority Priority);

    public static void MapStudiesV2(this IEndpointRouteBuilder app)
    {
        var v2 = app.MapGroup("/api/v2").WithGroupName("v2");

        v2.MapGet("/studies", (StudyRepository repo) =>
            TypedResults.Ok(repo.All().Select(ToV2).ToList()));

        v2.MapGet("/studies/{id}", Results<Ok<StudyV2>, ProblemHttpResult> (string id, StudyRepository repo) =>
                repo.Find(id) is { } study
                    ? TypedResults.Ok(ToV2(study))
                    : TypedResults.Problem(statusCode: 404, title: "Study not found", detail: $"No study with id '{id}'."))
          .ProducesProblem(StatusCodes.Status404NotFound);
    }

    private static StudyV2 ToV2(Study s) => new(
        Id:       s.Id,
        Patient:  new PatientV2(s.Patient.Hn, s.Patient.Name),
        Modality: s.Modality,
        Priority: s.Priority);
}
