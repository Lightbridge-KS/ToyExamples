using ToyRetrieve.Domain;

namespace ToyRetrieve.Retrievers;

/// <summary>
/// DECORATOR: same interface, adds behavior around another retriever.
/// "Try C-GET; if the PACS refuses, use C-MOVE." Neither strategy changes.
/// The same shape works for retry, logging, timing, caching...
/// </summary>
public sealed class FallbackRetriever(IStudyRetriever primary, IStudyRetriever fallback) : IStudyRetriever
{
    public async Task<RetrieveResult> RetrieveAsync(
        string studyUid, IInstanceSink sink, CancellationToken ct = default)
    {
        try
        {
            return await primary.RetrieveAsync(studyUid, sink, ct);
        }
        catch (NotSupportedException ex)
        {
            Console.WriteLine($"  [Fallback] {ex.Message} → trying fallback");
            return await fallback.RetrieveAsync(studyUid, sink, ct);
        }
    }
}
