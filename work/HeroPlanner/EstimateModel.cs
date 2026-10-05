using System.Text.Json;

namespace TilesSurviveHeroPlanner;

public sealed class EstimateData
{
    public Dictionary<string, EstimateHero> Heroes { get; set; } = [];
    public double[] Scales { get; set; } = [];
    public static EstimateData Parse(string json) => JsonSerializer.Deserialize<EstimateData>(json,
        new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower })!;
}
public sealed class EstimateHero
{
    public string ReferenceStage { get; set; } = "";
    public int ReferenceLevel { get; set; }
    public double[] ReferenceStats { get; set; } = [];
    public List<EstimateSkill> Skills { get; set; } = [];
}
public sealed class EstimateSkill
{
    public string Id { get; set; } = "";
    public int Slot { get; set; }
    public int ReferenceLevel { get; set; }
    public List<EstimateSkillLevel> Levels { get; set; } = [];
}
public sealed class EstimateSkillLevel
{
    public int Level { get; set; }
    public double Damage { get; set; }
    public double Utility { get; set; }
}
public sealed record HeroEstimate(double Offense, double Durability, double Score, double Low, double High, string Basis);

public static class EstimateModel
{
    public static HeroEstimate Evaluate(string slug, HeroBuild? saved, UpgradeData upgrades, EstimateData estimates)
    {
        var model = estimates.Heroes[slug]; var data = upgrades.Heroes[slug];
        var stage = data.Stages.Find(s => s.Id == saved?.Stage) ?? data.Stages.Find(s => s.Id == model.ReferenceStage)!;
        int levelNumber = Math.Min(saved?.Level is int n && data.Levels.Any(l => l.Level == n) ? n : model.ReferenceLevel, stage.LevelMax);
        var level = data.Levels.Find(l => l.Level == levelNumber)!;
        var stats = stage.Stats.Select((v, i) => v + level.Stats[i]).ToArray();
        int known = (saved?.Stage == stage.Id ? 1 : 0) + (saved?.Level == levelNumber ? 1 : 0);
        var slots = new HashSet<int>(); bool gearKnown = saved?.Gear is not null;
        foreach (var gear in saved?.Gear ?? [])
        {
            if (gear is not null && upgrades.Gear.TryGetValue(gear.Id, out var type) && type.HeroLevelRequired <= levelNumber &&
                type.Levels.Find(l => l.Level == gear.Level) is { } row && slots.Add(type.Slot))
                for (int i = 0; i < 3; i++) stats[i] += row.Stats[i];
            else gearKnown = false;
        }
        if (gearKnown) known++;
        double damage = 0, utility = 0;
        foreach (var skill in model.Skills)
        {
            int cap = stage.SkillCaps.ElementAtOrDefault(skill.Slot);
            int skillLevel = Math.Min(skill.ReferenceLevel, cap);
            if (saved?.Skills is not null && saved.Skills.TryGetValue(skill.Id, out int recorded) && recorded >= 0 && recorded <= cap && skill.Levels.Any(l => l.Level == recorded))
            { skillLevel = recorded; known++; }
            var row = skill.Levels.Find(l => l.Level == skillLevel) ?? skill.Levels[0];
            damage += row.Damage; utility += row.Utility;
        }
        (double offense, double durability, double score) Calculate(double damageFactor, double utilityFactor)
        {
            double o = 100 * stats[0] * (1 + .5 * Math.Log(1 + damage * damageFactor)) / estimates.Scales[0];
            double d = 100 * (.7 * stats[2] + 30 * stats[1]) * (1 + .08 * utility * utilityFactor) / estimates.Scales[1];
            double u = 100 * (1 + utility * utilityFactor) / estimates.Scales[2];
            return (o, d, .55 * o + .35 * d + .1 * u);
        }
        var typical = Calculate(1, 1);
        return new(typical.offense, typical.durability, typical.score, Calculate(.5, .5).score, Calculate(2.5, 1.5).score,
            known == 0 ? "Reference build" : known == model.Skills.Count + 3 ? "Recorded build" : "Recorded + assumed");
    }
}
