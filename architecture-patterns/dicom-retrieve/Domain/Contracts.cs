// ─────────────────────────────────────────────────────────────────────────────
// THE PORT: what the app needs, in its own words.
// Nothing in this file knows about C-GET, C-MOVE, AE titles, or TCP ports.
// ─────────────────────────────────────────────────────────────────────────────
namespace ToyRetrieve.Domain;

/// <summary>A DICOM instance, stripped down to the two UIDs this toy needs.</summary>
public sealed record DicomInstance(string StudyUid, string SopInstanceUid);

/// <summary>
/// Protocol-neutral outcome. Both C-GET and C-MOVE final responses carry
/// Completed/Failed counts, so this maps cleanly from either.
/// </summary>
public sealed record RetrieveResult(int Completed, int Failed);

/// <summary>
/// Where retrieved instances land. The CALLER owns it (save to disk, queue,
/// feed an AI model...). Retrievers only deliver into it.
/// </summary>
public interface IInstanceSink
{
    Task OnInstanceAsync(DicomInstance instance, CancellationToken ct);
}

/// <summary>
/// STRATEGY: "bring this study into my sink."
/// HOW (pull vs push, one association vs two) is the implementation's business.
/// </summary>
public interface IStudyRetriever
{
    Task<RetrieveResult> RetrieveAsync(
        string studyUid, IInstanceSink sink, CancellationToken ct = default);
}
