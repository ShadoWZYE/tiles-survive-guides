namespace TilesSurviveHeroPlanner;

public sealed record FormationEvaluation(Hero[] Heroes, double Adjustment, double FrontDurability);

public static class FormationModel
{
    // Conservative planning prior, not a fitted targeting probability.
    public const double FrontWeight = .75;
    private static double[] TeamTotal(Hero[] heroes)
    {
        double[] total=[0,0,0];
        foreach(var h in heroes)for(int i=0;i<3;i++) total[i]+=h.Estimate?.TeamPercent?.ElementAtOrDefault(i) ?? 0;
        return total;
    }
    private static double Delta(double[] total,Hero hero,int i) =>
        (total[i]-(hero.Estimate?.TeamPercent?.ElementAtOrDefault(i) ?? 0))*(hero.Estimate?.PassiveContributions?.ElementAtOrDefault(i) ?? 0);
    public static double PassiveBonus(IEnumerable<Hero> source, PlannerMode mode)
    {
        var heroes = source.ToArray();
        if(heroes.Length == 0 || heroes.Any(h => h.Estimate?.Basis == "Flat max stats")) return 0;
        var total=TeamTotal(heroes);
        if(total.All(v => v==0))return 0;
        double offense = mode switch { PlannerMode.Survival => .1375, PlannerMode.Offense => .8875, PlannerMode.Pve => .5875, _ => .55 };
        double defense = mode switch { PlannerMode.Survival => .8375, PlannerMode.Offense => .0875, PlannerMode.Pve => .3875, _ => .35 };
        return heroes.Average(h => offense*Delta(total,h,0)+defense*(Delta(total,h,1)+Delta(total,h,2)));
    }
    public static FormationEvaluation Evaluate(IEnumerable<Hero> source, PlannerMode mode, double healthBonus = 0, double exposure = FrontWeight)
    {
        var heroes = source.ToArray();
        var legacy = heroes.OrderBy(h => h.Role switch { "Melee" => 0, "Mid" => 1, "Range" => 2, _ => 3 })
            .ThenByDescending(h => h.Role == "Melee" ? h.DurabilityIndex : h.OffenseIndex)
            .ThenBy(h => h.AssetSlug, StringComparer.Ordinal).ToArray();
        if (heroes.Length != 5 || heroes.Any(h => h.Estimate?.Basis == "Flat max stats")) return new(legacy, 0, 0);
        var total=TeamTotal(heroes);
        double Durability(Hero h) => Math.Max(0, h.DurabilityIndex + h.HealthContribution * healthBonus + Delta(total,h,1)+Delta(total,h,2));
        var candidates = heroes.Where(h => h.Role is "Melee" or "Mid").ToArray();
        var front = (candidates.Length >= 2 ? candidates : heroes).OrderByDescending(Durability)
            .ThenBy(h => h.OffenseIndex).ThenBy(h => h.AssetSlug, StringComparer.Ordinal).Take(2).ToArray();
        var back = heroes.Except(front).OrderByDescending(h => h.OffenseIndex).ThenBy(h => h.AssetSlug, StringComparer.Ordinal).ToArray();
        double a = Durability(front[0]), b = Durability(front[1]);
        double frontDurability = a + b > 0 ? 2 * a * b / (a + b) : 0;
        double weight = mode switch { PlannerMode.Survival => .8375, PlannerMode.Offense => .0875, PlannerMode.Pve => .3875, _ => .35 };
        double adjustment = weight * (exposure * frontDurability + (1 - exposure) * back.Average(Durability) - heroes.Average(Durability));
        return new([.. front, .. back], adjustment, frontDurability);
    }
}
