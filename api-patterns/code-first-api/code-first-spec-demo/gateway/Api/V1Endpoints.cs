using Gateway.Domain;
using Microsoft.AspNetCore.Http.HttpResults;

namespace Gateway.Api;

/// <summary>
/// Contract v1 on <c>/api/v1</c>.
///
/// In code-first, THIS FILE is the source of the contract. The record below
/// is no longer a hand-copy of a YAML schema: the YAML is derived from it.
/// </summary>
public static class V1Endpoints
{
    /// <summary>Wire format of contract v1.</summary>
    /// <remarks>
    /// A parameter WITHOUT a default value → "required" in the spec.
    /// A parameter WITH a default value    → optional (priority was added in 1.1.0).
    /// Prefer a default over a nullable enum (Priority?): in OpenAPI 3.1 the generator
    /// emits enum [..., null], which client generators turn into a junk enum member.
    /// </remarks>
    public sealed record StudyV1(string Id, string PatientName, Modality Modality, Priority Priority = Priority.Routine);

    public static void MapStudiesV1(this IEndpointRouteBuilder app)
    {
        var v1 = app.MapGroup("/api/v1").WithGroupName("v1");

        // TypedResults (not Results) let the generator SEE the response types.
        v1.MapGet("/studies", (StudyRepository repo) =>
            TypedResults.Ok(repo.All().Select(ToV1).ToList()));

        v1.MapGet("/studies/{id}", Results<Ok<StudyV1>, ProblemHttpResult> (string id, StudyRepository repo) =>
                repo.Find(id) is { } study
                    ? TypedResults.Ok(ToV1(study))
                    : TypedResults.Problem(statusCode: 404, title: "Study not found", detail: $"No study with id '{id}'."))
          .ProducesProblem(StatusCodes.Status404NotFound);
    }

    private static StudyV1 ToV1(Study s) => new(
        Id:          s.Id,
        PatientName: s.Patient.Name,
        Modality:    s.Modality,
        Priority:    s.Priority);
}
