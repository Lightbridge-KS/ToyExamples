using ToyRetrieve.Domain;
using ToyRetrieve.Simulated;

namespace ToyRetrieve.Retrievers;

/// <summary>
/// STRATEGY #1: pull. Instances arrive as callbacks on our own association,
/// so we can wire them straight into the sink. No listener, no router.
/// </summary>
public sealed class CGetRetriever(FakePacs pacs) : IStudyRetriever
{
    public Task<RetrieveResult> RetrieveAsync(
        string studyUid, IInstanceSink sink, CancellationToken ct = default)
        => pacs.CGetAsync(studyUid, instance => sink.OnInstanceAsync(instance, ct));
}
