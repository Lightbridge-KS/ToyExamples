// ─────────────────────────────────────────────────────────────────────────────
// COMPOSITION ROOT: the only place that knows which strategy goes with which
// PACS. Everything below `Retrieve(...)` is caller code, and it never changes.
// ─────────────────────────────────────────────────────────────────────────────
using ToyRetrieve.Domain;
using ToyRetrieve.Receiving;
using ToyRetrieve.Retrievers;
using ToyRetrieve.Simulated;

const string MyAe = "RAMAAI";
const string ChestCt = "1.2.3.100";
const string BrainMr = "1.2.3.200";

var archive = new[]
{
    new DicomInstance(ChestCt, "1.2.3.100.1"),
    new DicomInstance(ChestCt, "1.2.3.100.2"),
    new DicomInstance(ChestCt, "1.2.3.100.3"),
    new DicomInstance(BrainMr, "1.2.3.200.1"),
    new DicomInstance(BrainMr, "1.2.3.200.2"),
};

// ── The outside world: one modern PACS, one legacy (C-MOVE only) ────────────
var modernPacs = new FakePacs("PACS-A", supportsCGet: true,  archive);
var legacyPacs = new FakePacs("PACS-B", supportsCGet: false, archive);

// ── Our receiving side: started ONCE at app startup, shared by all moves ────
var router   = new MoveRouter();
var storeScp = new StoreScp(router);
legacyPacs.RegisterMoveDestination(MyAe, storeScp);   // done by the PACS admin

// ── FACTORY: per-PACS config → strategy ─────────────────────────────────────
IStudyRetriever For(FakePacs pacs, string mode) => mode switch
{
    "CGET"  => new CGetRetriever(pacs),
    "CMOVE" => new CMoveRetriever(pacs, router, MyAe),
    "AUTO"  => new FallbackRetriever(
                   new CGetRetriever(pacs),
                   new CMoveRetriever(pacs, router, MyAe)),
    _ => throw new ArgumentException($"unknown mode '{mode}'"),
};

await Retrieve("1. C-GET on PACS-A", For(modernPacs, "CGET"), ChestCt);
await Retrieve("2. C-MOVE on PACS-B", For(legacyPacs, "CMOVE"), ChestCt);
await Retrieve("3. AUTO on PACS-B (C-GET refused → C-MOVE)", For(legacyPacs, "AUTO"), BrainMr);

// 4. Why the router exists: two moves in flight, ONE listener.
//    C-STOREs interleave on the wire; the router keeps them apart.
Header("4. Two C-MOVEs at once on PACS-B");
var mover = For(legacyPacs, "CMOVE");
await Task.WhenAll(
    mover.RetrieveAsync(ChestCt, new PrintingSink(ChestCt)),
    mover.RetrieveAsync(BrainMr, new PrintingSink(BrainMr)));

// ── CALLER CODE ─────────────────────────────────────────────────────────────
// Identical for every strategy. No C-GET, no C-MOVE, no AE titles, no ports.
static async Task Retrieve(string title, IStudyRetriever retriever, string studyUid)
{
    Header(title);
    var result = await retriever.RetrieveAsync(studyUid, new PrintingSink(studyUid));
    Console.WriteLine($"  => {result}");
}

static void Header(string title) => Console.WriteLine($"\n=== {title} ===");

/// <summary>
/// The caller's sink. Real life: write .dcm to disk, enqueue for an AI model...
/// The ✓/✗ check proves each instance reached the sink that asked for it.
/// </summary>
sealed class PrintingSink(string expectedStudyUid) : IInstanceSink
{
    public Task OnInstanceAsync(DicomInstance instance, CancellationToken ct)
    {
        var check = instance.StudyUid == expectedStudyUid ? "✓" : "✗ WRONG STUDY";
        Console.WriteLine($"      [Sink {expectedStudyUid}] got {instance.SopInstanceUid} {check}");
        return Task.CompletedTask;
    }
}
