using System.Text.Json;
using System.IO;
using System.Text.Json.Serialization;

namespace TilesSurviveHeroPlanner;

public sealed class HeroBuild
{
    public string? Stage { get; set; }
    public int? Level { get; set; }
    public Dictionary<string, int> Skills { get; set; } = [];
    public List<GearBuild>? Gear { get; set; }
    public HeroBuild Copy() => new() { Stage = Stage, Level = Level, Skills = new(Skills ?? []), Gear = Gear?.Select(g => new GearBuild { Id = g.Id, Level = g.Level }).ToList() };
}
public sealed class GearBuild { public string Id { get; set; } = ""; public int Level { get; set; } }
public sealed class UpgradeSettings
{
    public string Goal { get; set; } = "power";
    public int Seconds { get; set; } = 30;
    public Dictionary<string, double> Inventory { get; set; } = [];
    public bool OnlyAffordable { get; set; }
    public string? TargetedPool { get; set; }
    public void Clean()
    {
        if (!UpgradeModel.Goals.Contains(Goal)) Goal = "power";
        if (Seconds is < 1 or > 300) Seconds = 30;
        Inventory = (Inventory ?? []).Where(x => double.IsFinite(x.Value) && x.Value is >= 0 and <= 1e12).ToDictionary();
    }
}
public sealed class UpgradeData
{
    public string ClientBuild { get; set; } = "";
    public Dictionary<string, UpgradeHero> Heroes { get; set; } = [];
    public Dictionary<string, UpgradeGear> Gear { get; set; } = [];
    public Dictionary<string, string> Items { get; set; } = [];
    public TargetedDraftData? TargetedDraft { get; set; }
    public static UpgradeData Parse(string json) => JsonSerializer.Deserialize<UpgradeData>(json,
        new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower }) ?? throw new InvalidDataException("Upgrade data missing.");
}
public sealed class TargetedDraftData
{
    public string CardItem { get; set; } = "";
    public List<TargetedPool> Pools { get; set; } = [];
    public string Notes { get; set; } = "";
}
public sealed class TargetedPool
{
    public string Id { get; set; } = "";
    public List<TargetedChoice> Choices { get; set; } = [];
    public int SingleCost { get; set; }
    public int Pity { get; set; }
    public int UnlockLevel { get; set; }
    public string SelectedHeroChance { get; set; } = "";
    public string SelectedShardChance { get; set; } = "";
    public string SelectedBonusChance { get; set; } = "";
}
public sealed class TargetedChoice
{
    public string Slug { get; set; } = "";
    public string HeroInternal { get; set; } = "";
    public string ShardItem { get; set; } = "";
}
public sealed record TargetedCandidate(string Slug, string Name, string Stage, int Rank, int Step,
    double Cost, double? Balance, double Remaining, double Gain, double? Efficiency, string? Blocked, int[] SkillCaps);
public sealed class TargetedResult
{
    public List<string> Missing { get; } = [];
    public List<TargetedCandidate> Candidates { get; set; } = [];
}
public sealed class UpgradeHero
{
    public string Name { get; set; } = "";
    public List<UpgradeStage> Stages { get; set; } = [];
    public List<UpgradeLevel> Levels { get; set; } = [];
    public List<UpgradeSkill> Skills { get; set; } = [];
}
public sealed class UpgradeStage
{
    public string Id { get; set; } = "";
    public int Rank { get; set; }
    public int Step { get; set; }
    public Dictionary<string, double> Cost { get; set; } = [];
    public double[] Stats { get; set; } = [0, 0, 0];
    public double Power { get; set; }
    public int[] SkillCaps { get; set; } = [];
    public string Unlocks { get; set; } = "";
    public int LevelRequired { get; set; }
    public int LevelMax { get; set; }
    public int BuildingRequired { get; set; }
}
public sealed class UpgradeLevel
{
    public int Level { get; set; }
    public double[] Stats { get; set; } = [0, 0, 0];
    public double Power { get; set; }
    public double? XpTotal { get; set; }
    public int? BuildingGate { get; set; }
}
public sealed class UpgradeSkill
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public int Slot { get; set; }
    public int EffectType { get; set; }
    public bool Conditional { get; set; }
    public double DamageRatio { get; set; }
    public double[] DamageParams { get; set; } = [];
    public double Cooldown { get; set; }
    public double FirstCast { get; set; }
    public List<UpgradeSkillLevel> Levels { get; set; } = [];
    [JsonIgnore] public bool DirectSupported => EffectType == 1 && DamageParams.Length > 0 && !Conditional && Cooldown > 0;
}
public sealed class UpgradeSkillLevel
{
    public int Level { get; set; }
    public double Power { get; set; }
    public Dictionary<string, double> Cost { get; set; } = [];
    public string[] Params { get; set; } = [];
}
public sealed class UpgradeGear
{
    public string Name { get; set; } = "";
    public int Slot { get; set; }
    public int Quality { get; set; }
    public int HeroLevelRequired { get; set; }
    public List<UpgradeGearLevel> Levels { get; set; } = [];
}
public sealed class UpgradeGearLevel
{
    public int Level { get; set; }
    public double[] Stats { get; set; } = [0, 0, 0];
    public double Power { get; set; }
    public double XpNext { get; set; }
}
public sealed record BuildState(HeroBuild Build, UpgradeStage Stage, UpgradeLevel Level, double[] Stats, double Power, double? Direct, List<string> Notes);
public sealed record UpgradeCandidate(string Slug, string Label, string Kind, Dictionary<string, double> Cost,
    string? Group, double? Gain, double? Efficiency, string Affordability, string Detail, string? Blocked, bool Unsupported, double[]? Delta);
public sealed class UpgradeResult
{
    public List<string> Missing { get; } = [];
    public List<string> Notes { get; } = [];
    public List<UpgradeCandidate> Candidates { get; set; } = [];
}

// Table-derived next-step comparisons. Runtime combat interpretations remain experimental.
public static class UpgradeModel
{
    public static readonly string[] Goals = ["power", "attack", "health", "defense", "direct"];
    private static double? Metric(BuildState s, string goal) => goal switch
    { "power" => s.Power, "direct" => s.Direct, "attack" => s.Stats[0], "defense" => s.Stats[1], _ => s.Stats[2] };
    public static TargetedResult EvaluateTargeted(IEnumerable<string> slugs, Dictionary<string, HeroBuild> builds,
        UpgradeData data, UpgradeSettings settings, TargetedPool pool)
    {
        var result = new TargetedResult(); var states = new Dictionary<string, BuildState>();
        foreach (var slug in slugs.Distinct())
        {
            var state = State(slug, builds.GetValueOrDefault(slug), data, settings.Seconds, out var error);
            if (state is null) result.Missing.Add($"{data.Heroes.GetValueOrDefault(slug)?.Name ?? slug}: {error}"); else states[slug] = state;
        }
        if (result.Missing.Count > 0 || states.Count == 0) return result;
        if (states.Values.Any(s => Metric(s, settings.Goal) is null)) { result.Missing.Add("The selected metric requires known direct-skill levels."); return result; }
        double total = states.Values.Sum(s => Metric(s, settings.Goal)!.Value);
        if (total <= 0) { result.Missing.Add("No positive formation baseline for this metric."); return result; }
        foreach (var choice in pool.Choices.Where(c => states.ContainsKey(c.Slug)).DistinctBy(c => c.Slug))
        {
            var before = states[choice.Slug]; var hero = data.Heroes[choice.Slug];
            int currentIndex = hero.Stages.IndexOf(before.Stage);
            // A completed six-step rank is the milestone; above the six-step range use the next configured rank.
            var remainingStages = hero.Stages.Skip(currentIndex + 1).ToList();
            var target = remainingStages.FirstOrDefault(s => s.Step == 6 || s.Rank > 10 && s.Step == 1);
            if (target is null) continue;
            var path = remainingStages.Take(remainingStages.IndexOf(target) + 1).ToList();
            if (path.Any(s => s.Cost.Count != 1 || !s.Cost.TryGetValue(choice.ShardItem, out double n) || n <= 0))
            { result.Missing.Add($"{hero.Name}: milestone cost is not entirely this hero's fragments; excluded."); continue; }
            double cost = path.Sum(s => s.Cost[choice.ShardItem]);
            double? balance = settings.Inventory.TryGetValue(choice.ShardItem, out double held) ? held : null;
            double remaining = Math.Max(0, cost - (balance ?? 0));
            var afterBuild = before.Build.Copy(); afterBuild.Stage = target.Id;
            var after = State(choice.Slug, afterBuild, data, settings.Seconds, out var error);
            if (after is null || Metric(after, settings.Goal) is not double afterMetric) { result.Missing.Add($"{hero.Name}: {error ?? "return unknown"}"); continue; }
            double gain = (afterMetric - Metric(before, settings.Goal)!.Value) / total * 100;
            string? blocked = path.Any(s => s.LevelRequired > before.Level.Level) ? $"Needs hero level {path.Max(s => s.LevelRequired)} before completing this milestone" : null;
            result.Candidates.Add(new(choice.Slug, hero.Name, target.Id, target.Rank, target.Step,
                cost, balance, remaining, gain, remaining > 0 && blocked is null ? gain / remaining * 100 : null, blocked, target.SkillCaps));
        }
        result.Candidates = result.Candidates.OrderByDescending(c => c.Efficiency ?? double.NegativeInfinity).ThenBy(c => c.Name, StringComparer.Ordinal).ToList();
        return result;
    }
    public static BuildState? State(string slug, HeroBuild? b, UpgradeData data, int seconds, out string? error)
    {
        error = null;
        if (b is null || !data.Heroes.TryGetValue(slug, out var h)) { error = "build not recorded"; return null; }
        var stage = h.Stages.Find(s => s.Id == b.Stage); var level = h.Levels.Find(l => l.Level == b.Level);
        if (stage is null || level is null) { error = "exact rank step / hero level missing"; return null; }
        if (level.Level > stage.LevelMax) { error = "hero level exceeds this rank's cap"; return null; }
        var stats = stage.Stats.Select((n, i) => n + level.Stats[i]).ToArray(); var power = stage.Power + level.Power;
        var notes = new List<string>(); var slots = new HashSet<int>();
        if (b.Gear is null) notes.Add("gear not recorded (excluded)");
        foreach (var g in b.Gear ?? [])
        {
            if (g is null || !data.Gear.TryGetValue(g.Id, out var type) || type.Levels.Find(l => l.Level == g.Level) is not { } entry ||
                !slots.Add(type.Slot) || type.HeroLevelRequired > b.Level)
            { error = "invalid, duplicate-slot or level-gated gear"; return null; }
            for (int i = 0; i < 3; i++) stats[i] += entry.Stats[i]; power += entry.Power;
        }
        var skills = b.Skills ?? []; double direct = 0; bool known = true;
        foreach (var skill in h.Skills)
        {
            if (!skills.TryGetValue(skill.Id, out int n)) { notes.Add($"{skill.Name}: skill level unknown; power excluded"); if (skill.DirectSupported) known = false; continue; }
            int cap = skill.Slot < stage.SkillCaps.Length ? stage.SkillCaps[skill.Slot] : 0;
            var sl = skill.Levels.Find(l => l.Level == n);
            if (n < 0 || n > cap || (n > 0 && sl is null)) { error = $"{skill.Name}: level exceeds cap or is absent from data"; return null; }
            if (n > 0) power += sl!.Power;
            if (!skill.DirectSupported || n == 0) continue;
            double coefficient = skill.DamageRatio * (skill.DamageParams[0] + skill.DamageParams.ElementAtOrDefault(1) * (n - 1));
            double casts = seconds * 1000 > skill.FirstCast ? Math.Ceiling((seconds * 1000 - skill.FirstCast) / skill.Cooldown) : 0;
            direct += stats[0] * coefficient * casts;
        }
        return new(b, stage, level, stats, power, known ? direct : null, notes);
    }
    public static UpgradeResult Evaluate(IEnumerable<string> slugs, Dictionary<string, HeroBuild> builds, UpgradeData data, UpgradeSettings settings)
    {
        settings.Clean(); var result = new UpgradeResult(); var states = new Dictionary<string, BuildState>();
        foreach (var slug in slugs.Distinct())
        {
            var s = State(slug, builds.GetValueOrDefault(slug), data, settings.Seconds, out var error);
            if (s is null) result.Missing.Add($"{data.Heroes.GetValueOrDefault(slug)?.Name ?? slug}: {error}"); else states[slug] = s;
        }
        if (result.Missing.Count > 0 || states.Count == 0) return result;
        double? Metric(BuildState s) => settings.Goal switch { "power" => s.Power, "direct" => s.Direct, "attack" => s.Stats[0], "defense" => s.Stats[1], _ => s.Stats[2] };
        double? total = states.Values.All(s => Metric(s) is not null) ? states.Values.Sum(s => Metric(s)!.Value) : null;
        void Add(string slug, string label, string kind, HeroBuild after, Dictionary<string, double> cost, string detail, string? blocked = null, bool unsupported = false)
        {
            var before = states[slug]; var next = State(slug, after, data, settings.Seconds, out var error);
            double? gain = !unsupported && next is not null && total > 0 && Metric(next) is double n && Metric(before) is double p ? (n - p) / total * 100 : null;
            cost = cost.Where(x => double.IsFinite(x.Value) && x.Value > 0).ToDictionary();
            string? group = cost.Count == 1 ? cost.Keys.First() : null;
            bool balancesKnown = cost.Count > 0 && cost.All(x => settings.Inventory.ContainsKey(x.Key));
            string affordability = !balancesKnown ? "unknown" : cost.All(x => settings.Inventory[x.Key] >= x.Value) ? "affordable" : "insufficient";
            blocked ??= error;
            double? efficiency = gain is not null && group is not null && blocked is null ? gain / cost[group] * 100 : null;
            if (settings.OnlyAffordable && (affordability != "affordable" || blocked is not null)) return;
            result.Candidates.Add(new(slug, label, kind, cost, group, gain, efficiency, affordability, detail, blocked, unsupported,
                next?.Stats.Select((v, i) => v - before.Stats[i]).ToArray()));
        }
        foreach (var (slug, s) in states)
        {
            var h = data.Heroes[slug]; result.Notes.AddRange(s.Notes.Select(n => h.Name + ": " + n));
            var rank = h.Stages.ElementAtOrDefault(h.Stages.IndexOf(s.Stage) + 1);
            if (rank is not null)
            {
                var after = s.Build.Copy(); after.Stage = rank.Id;
                Add(slug, $"{h.Name}: rank {s.Stage.Rank}/{s.Stage.Step} → {rank.Rank}/{rank.Step}", "rank", after, rank.Cost,
                    $"Skill caps {string.Join('/', rank.SkillCaps)}. Unlocks {rank.Unlocks}. Building requirement {rank.BuildingRequired}: check in-game.",
                    s.Build.Level < rank.LevelRequired ? $"Requires hero level {rank.LevelRequired}" : null);
            }
            var level = h.Levels.Find(l => l.Level == s.Build.Level + 1);
            if (level is not null)
            {
                var after = s.Build.Copy(); after.Level = level.Level; var xp = level.XpTotal - s.Level.XpTotal;
                Add(slug, $"{h.Name}: level {s.Build.Level} → {level.Level}", "level", after, xp > 0 ? new() { ["hero-xp"] = xp.Value } : [],
                    $"Building gate {level.BuildingGate}: check in-game. Assumes zero XP toward next level.", level.Level > s.Stage.LevelMax ? "Rank level cap reached" : null);
            }
            foreach (var skill in h.Skills)
            {
                if (!(s.Build.Skills ?? []).TryGetValue(skill.Id, out int n)) continue;
                var next = skill.Levels.Find(l => l.Level == n + 1); if (next is null) continue;
                int cap = s.Stage.SkillCaps.ElementAtOrDefault(skill.Slot); var after = s.Build.Copy(); after.Skills[skill.Id] = n + 1;
                Add(slug, $"{h.Name}: {skill.Name} {n} → {n + 1}", "skill", after, next.Cost,
                    "SlgItemReq cost. " + (skill.DirectSupported ? "Experimental affine direct-output potential; animation/mitigation excluded. " : "Runtime utility/conditional effect not simulated. ") + string.Join(';', next.Params),
                    n + 1 > cap ? $"Needs higher rank (current cap {cap})" : null, settings.Goal == "direct" && !skill.DirectSupported);
            }
            foreach (var g in s.Build.Gear ?? [])
            {
                var type = data.Gear[g.Id]; var current = type.Levels.Find(l => l.Level == g.Level)!; var next = type.Levels.Find(l => l.Level == g.Level + 1);
                if (next is null) continue; var after = s.Build.Copy(); after.Gear!.Find(x => x.Id == g.Id)!.Level++;
                Add(slug, $"{h.Name}: {type.Name} {g.Level} → {next.Level}", "gear", after,
                    current.XpNext > 0 ? new() { ["gear-xp"] = current.XpNext } : [], "Gear level only; refinement/enhancement/exclusive effects excluded. Assumes zero next-level XP progress.");
            }
        }
        result.Candidates = result.Candidates.OrderBy(c => c.Group ?? "~", StringComparer.Ordinal).ThenByDescending(c => c.Efficiency ?? double.NegativeInfinity).ThenBy(c => c.Label, StringComparer.Ordinal).ToList();
        return result;
    }
}
