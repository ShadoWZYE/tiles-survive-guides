using System.Text.Json;
using TilesSurviveHeroPlanner;

if (args.Length > 2 && args[1] == "--targeted")
{
    var data = UpgradeData.Parse(File.ReadAllText(args[2]));
    void Assert(bool condition, string message) { if (!condition) throw new Exception(message); }
    var pool = data.TargetedDraft!.Pools.Single(p => p.Id == "newbie_recuit_up_1");
    var slugs = new[] { "rosie", "layla", "becca", "ray", "maddie" };
    var builds = slugs.ToDictionary(s => s, s => new HeroBuild { Stage = data.Heroes[s].Stages[0].Id, Level = 1, Gear = [] });
    var settings = new UpgradeSettings { Goal = "attack" };
    var initial = UpgradeModel.EvaluateTargeted(slugs, builds, data, settings, pool);
    Assert(initial.Candidates.Count == 3 && initial.Candidates.All(c => new[] { "rosie", "ray", "maddie" }.Contains(c.Slug)), "Unavailable hero recommended");
    var rosie = initial.Candidates.Single(c => c.Slug == "rosie");
    Assert(rosie.Cost == 15 && rosie.Balance is null && rosie.Remaining == 15, "Full milestone cost / unknown balance wrong");
    builds["rosie"].Stage = data.Heroes["rosie"].Stages.Single(s => s.Rank == 1 && s.Step == 5).Id;
    var near = UpgradeModel.EvaluateTargeted(slugs, builds, data, settings, pool).Candidates.Single(c => c.Slug == "rosie");
    Assert(near.Cost == 3 && near.Rank == 1 && near.Step == 6, "Partial progress did not reduce remaining cost");
    settings.Inventory["207076"] = 2;
    var shortOne = UpgradeModel.EvaluateTargeted(slugs, builds, data, settings, pool).Candidates.Single(c => c.Slug == "rosie");
    Assert(shortOne.Remaining == 1 && Math.Abs(shortOne.Efficiency!.Value - shortOne.Gain * 100) < 1e-8, "Recorded fragments ignored");
    settings.Inventory["207076"] = 100;
    var paid = UpgradeModel.EvaluateTargeted(slugs, builds, data, settings, pool).Candidates.Single(c => c.Slug == "rosie");
    Assert(paid.Remaining == 0 && paid.Efficiency is null, "Already affordable milestone incorrectly promotes further pulls");
    builds.Remove("becca");
    Assert(UpgradeModel.EvaluateTargeted(slugs, builds, data, settings, pool).Candidates.Count == 0, "Missing formation build produced a ranking");
    Assert(data.TargetedDraft.Pools.All(p => p.SingleCost > 0 && p.Choices.Count > 0), "Invalid pool extraction");
    Console.WriteLine("Targeted Draft tests passed: eligibility, milestone path, partial rank, known/unknown balances, already affordable, incomplete formation.");
    return;
}

if (args.Length > 2 && args[1] == "--upgrades")
{
    var data = UpgradeData.Parse(File.ReadAllText(args[2]));
    var upgradeCases = new List<object>();
    var slugs = new[] { "rosie", "layla", "becca", "ray", "maddie" };
    foreach (int step in new[] { 0, 5, 20, 40 })
    foreach (string goal in UpgradeModel.Goals)
    foreach (string gearMode in new[] { "unknown", "none", "recorded" })
    {
        var builds = slugs.ToDictionary(s => s, s => {
            var h = data.Heroes[s]; var stage = h.Stages[Math.Min(step, h.Stages.Count - 1)];
            var build = new HeroBuild { Stage = stage.Id, Level = Math.Min(1 + step, stage.LevelMax), Gear = gearMode == "unknown" ? null : [],
                Skills = h.Skills.ToDictionary(k => k.Id, k => Math.Min(2, stage.SkillCaps.ElementAtOrDefault(k.Slot))) };
            if (gearMode == "recorded")
            {
                var gear = data.Gear.FirstOrDefault(g => g.Value.HeroLevelRequired <= build.Level);
                if (gear.Key is not null) build.Gear!.Add(new() { Id = gear.Key, Level = gear.Value.Levels[0].Level });
            }
            if (gearMode == "unknown") build.Skills.Remove(h.Skills[0].Id);
            return build;
        });
        var settings = new UpgradeSettings { Goal = goal, Inventory = new() { ["hero-xp"] = 10000, ["201725"] = 30 }, Seconds = 30 };
        var result = UpgradeModel.Evaluate(slugs, builds, data, settings);
        upgradeCases.Add(new { id = $"{step}/{goal}/{gearMode}", slugs, builds, settings, candidates = result.Candidates, missing = result.Missing });
    }
    Console.WriteLine(JsonSerializer.Serialize(upgradeCases, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
    return;
}

var heroes = JsonSerializer.Deserialize<List<Hero>>(File.ReadAllText(args[0]))!;
var example = new[] { "Rosie", "Layla", "Becca", "Ray", "Maddie" }.Select(name => heroes.Single(h => h.Name == name)).ToList();
void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
Check(example.Single(h => h.Name == "Becca").HasMechanic("DEF reduction"), "Becca DEF break not detected");
var expected = new Dictionary<PlannerMode, string[]> {
    [PlannerMode.Balanced] = ["Becca", "Rosie", "Ray", "Layla", "Maddie"],
    [PlannerMode.Pve] = ["Becca", "Rosie", "Ray", "Layla", "Maddie"],
    [PlannerMode.Offense] = ["Becca", "Ray", "Rosie", "Layla", "Maddie"],
    [PlannerMode.Survival] = ["Rosie", "Layla", "Becca", "Ray", "Maddie"],
};
foreach (var (mode, names) in expected)
    Check(FormationPriority.Rank(example, mode).Select(x => x.Hero.Name).SequenceEqual(names), $"Unexpected {mode} example order");
var progress = new HeroProgress { Current = 4, Target = 4 };
Check(progress.Status == "reached", "Reached star target");
progress.Target = 5;
Check(progress.Status == "pending", "Pending star target");
progress.Current = null;
Check(progress.Status == "unknown", "Unknown is not zero stars");
Check(HeroProgress.Clean(-1) is null && HeroProgress.Clean(100) is null && HeroProgress.Clean(0) == 0, "Star validation");
var old = JsonSerializer.Deserialize<PlannerProfile>("{\"owned_heroes\":[\"becca\"]}")!;
Check(old.OwnedHeroes.Contains("becca") && old.HeroProgress.Count == 0, "Old profile migration");
old.HeroProgress["becca"] = new() { Current = 3, Target = 4 };
var restored = JsonSerializer.Deserialize<PlannerProfile>(JsonSerializer.Serialize(old))!;
Check(restored.HeroProgress["becca"].Current == 3 && restored.HeroProgress["becca"].Status == "pending", "Profile round trip");

var cases = new Dictionary<string, IEnumerable<Hero>> {
    ["example"] = example,
    ["reversed"] = example.AsEnumerable().Reverse(),
    ["duplicates"] = example.Concat(example),
    ["empty"] = [],
    ["frontOnly"] = heroes.Where(h => h.Role == "Melee").Take(5),
    ["noFront"] = heroes.Where(h => h.Role != "Melee").Take(5),
    ["partial"] = example.Take(2),
    ["tied"] = heroes.Where(h => h.OffenseIndex == 74.09).Take(5),
};
var output = new Dictionary<string, object>();
foreach (var (name, squad) in cases)
foreach (var mode in Enum.GetValues<PlannerMode>())
{
    var rank = FormationPriority.Rank(squad, mode);
    Check(rank.Select(x => x.Hero.AssetSlug).Distinct().Count() == squad.Select(h => h.AssetSlug).Distinct().Count(), $"Lost/duplicate hero {name}/{mode}");
    output[$"{name}/{mode}"] = rank.Select(x => new { slug = x.Hero.AssetSlug, reason = x.Reason });
}
Console.WriteLine(JsonSerializer.Serialize(output));
