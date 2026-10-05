using System.Text.Json;
using TilesSurviveHeroPlanner;

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
