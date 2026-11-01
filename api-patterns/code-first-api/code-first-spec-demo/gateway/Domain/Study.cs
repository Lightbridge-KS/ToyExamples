namespace Gateway.Domain;

// ─────────────────────────────────────────────────────────────────────
// INTERNAL model — free to change. Never serialized directly.
// The public contracts are the DTO records in Api/V1Endpoints.cs and
// Api/V2Endpoints.cs, mapped from this.
// ─────────────────────────────────────────────────────────────────────

public enum Modality { CT, MR, US, XR, MG }
public enum Priority { Routine, Stat }

public sealed record Patient(string Hn, string Name);
public sealed record Study(string Id, Patient Patient, Modality Modality, Priority Priority);

/// <summary>Stub data source. A real gateway would proxy to backend services.</summary>
public sealed class StudyRepository
{
    private readonly List<Study> _studies =
    [
        new("S-001", new Patient("6512345", "Somchai Jaidee"),  Modality.CT, Priority.Stat),
        new("S-002", new Patient("6598765", "Malee Srisuk"),    Modality.MR, Priority.Routine),
        new("S-003", new Patient("6600001", "Wanida Thongdee"), Modality.MG, Priority.Routine),
    ];

    public IReadOnlyList<Study> All() => _studies;
    public Study? Find(string id) => _studies.FirstOrDefault(s => s.Id == id);
}
