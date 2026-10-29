using ToyRetrieve.Domain;
using ToyRetrieve.Receiving;
using ToyRetrieve.Simulated;

namespace ToyRetrieve.Retrievers;

/// <summary>
/// STRATEGY #2: push. We can't receive the instances ourselves; the PACS
/// pushes them to our StoreScp. So: tell the router where they should go,
/// ask the PACS to move, and wait for the final status.
/// </summary>
public sealed class CMoveRetriever(FakePacs pacs, MoveRouter router, string myAeTitle) : IStudyRetriever
{
    private static int _lastMessageId;

    public async Task<RetrieveResult> RetrieveAsync(
        string studyUid, IInstanceSink sink, CancellationToken ct = default)
    {
        int messageId = Interlocked.Increment(ref _lastMessageId);

        using var _ = router.Register(messageId, sink);                 // 1. register first
        return await pacs.CMoveAsync(studyUid, myAeTitle, messageId);  // 2. then ask
    }                                                                   // 3. unregister on final response
}
