// ─────────────────────────────────────────────────────────────────────────────
// THE OUTSIDE WORLD (stub). Stands in for a remote PACS *and* fo-dicom's
// network layer. Real code opens TCP associations; the toy just calls methods.
// ─────────────────────────────────────────────────────────────────────────────
using ToyRetrieve.Domain;

namespace ToyRetrieve.Simulated;

/// <summary>
/// A C-STORE that a PACS sends during a C-MOVE. It carries the
/// Move Originator Message ID, tag (0000,1031): "which C-MOVE caused me".
/// </summary>
public sealed record CStoreRequest(DicomInstance Instance, int MoveOriginatorMessageId);

/// <summary>Anything listening on a network port for incoming C-STOREs.</summary>
public interface ICStoreListener
{
    Task OnCStoreAsync(CStoreRequest request);
}

public sealed class FakePacs(string name, bool supportsCGet, IEnumerable<DicomInstance> archive)
{
    private readonly List<DicomInstance> _archive = archive.ToList();

    // The PACS's own config: "AE title X lives at host:port".
    private readonly Dictionary<string, ICStoreListener> _aeTable = new();

    /// <summary>What a PACS admin does once, in the PACS config screen.</summary>
    public void RegisterMoveDestination(string aeTitle, ICStoreListener listener)
        => _aeTable[aeTitle] = listener;

    /// <summary>
    /// C-GET (pull): instances come back on the SAME association,
    /// i.e. straight into the caller's callback.
    /// </summary>
    public async Task<RetrieveResult> CGetAsync(string studyUid, Func<DicomInstance, Task> onCStore)
    {
        if (!supportsCGet)
            throw new NotSupportedException($"{name} refused C-GET (not supported)");

        var hits = Find(studyUid);
        Console.WriteLine($"  [{name}] C-GET {studyUid}: sending {hits.Count} back on the same association");

        foreach (var instance in hits)
        {
            await Task.Delay(5);          // pretend network latency
            await onCStore(instance);     // same association → caller's callback
        }
        return new RetrieveResult(hits.Count, Failed: 0);
    }

    /// <summary>
    /// C-MOVE (push): the PACS opens a NEW association TO the destination AE
    /// and pushes instances there. The caller only gets the final status.
    /// </summary>
    public async Task<RetrieveResult> CMoveAsync(string studyUid, string destinationAe, int messageId)
    {
        if (!_aeTable.TryGetValue(destinationAe, out var listener))
            throw new InvalidOperationException($"{name}: unknown move destination '{destinationAe}'");

        var hits = Find(studyUid);
        Console.WriteLine($"  [{name}] C-MOVE {studyUid} (msgId={messageId}): dialing '{destinationAe}' on a NEW association");

        foreach (var instance in hits)
        {
            await Task.Delay(5);
            await listener.OnCStoreAsync(new CStoreRequest(instance, messageId)); // PACS dials YOU
        }
        return new RetrieveResult(hits.Count, Failed: 0);
    }

    private List<DicomInstance> Find(string studyUid)
        => _archive.Where(i => i.StudyUid == studyUid).ToList();
}
