namespace TilesSurviveHeroPlanner;

public sealed record FactionEffect(string Pattern, double HealthBonus, double CounterBonus, int Mariners)
{
    public string Summary => $"Faction {Pattern}: Final Health +{HealthBonus:P0}" +
        (Mariners > 0 ? $" ({Mariners} Mariner wildcard{(Mariners == 1 ? "" : "s")})" : "") +
        (CounterBonus > 0 ? $"; counter damage +{CounterBonus:P0} when applicable" : "");
}

// Screenshot-confirmed health tiers, including the fifth tier from current game_configs.
// Each Mariner occupies exactly one slot; it cannot be counted in both sides of a 3+2.
public static class FactionModel
{
    private static readonly Dictionary<string, FactionEffect> Cache = [];
    public static string Normalize(string? faction) => faction?.Trim().ToLowerInvariant() switch
    {
        "mountain" or "stalwart" => "Mountain",
        "wasteland" or "rover" => "Wasteland",
        "sky" or "aeronaut" => "Sky",
        "sea" or "mariner" => "Sea",
        _ => "Unknown",
    };

    public static FactionEffect Compose(IEnumerable<string> factions)
    {
        int mountain = 0, wasteland = 0, sky = 0, sea = 0, total = 0;
        foreach (string f in factions)
        {
            total++;
            switch (Normalize(f))
            {
                case "Mountain": mountain++; break;
                case "Wasteland": wasteland++; break;
                case "Sky": sky++; break;
                case "Sea": sea++; break;
            }
        }
        if (total > 5) throw new ArgumentException("A formation has at most five heroes.");
        string key = $"{mountain},{wasteland},{sky},{sea}";
        if (Cache.TryGetValue(key, out var cached)) return cached;
        var best = new FactionEffect("mixed", 0, 0, sea);
        for (int a = 0; a <= sea; a++)
        for (int b = 0; b <= sea - a; b++)
        {
            int[] counts = [mountain + a, wasteland + b, sky + sea - a - b];
            Array.Sort(counts);
            (string pattern, double hp, double counter) = counts[2] switch
            {
                5 => ("5", .25, .05),
                4 => ("4", .18, .05),
                3 when counts[1] == 2 => ("3+2", .12, .05),
                3 => ("3", .08, 0),
                2 when counts[1] == 2 => ("2+2", .04, 0),
                2 => ("2", .02, 0),
                _ => ("mixed", 0, 0),
            };
            if (hp > best.HealthBonus) best = new(pattern, hp, counter, sea);
        }
        Cache[key] = best;
        return best;
    }

    public static bool Counters(string attacker, string target) => (Normalize(attacker), Normalize(target)) switch
    {
        ("Wasteland", "Mountain") or ("Mountain", "Sky") or ("Sky", "Wasteland") => true,
        _ => false, // Mariners provide composition wildcards, not automatic counter damage.
    };

    // Apply health only to the HP component, not DEF, offense, utility or skill synergy.
    // Optional counter scenario assumes attacks land on the selected enemy faction.
    public static double ScoreBonus(IReadOnlyList<Hero> heroes, PlannerMode mode, string enemyFaction = "Unknown")
    {
        if (heroes.Count == 0) return 0;
        var effect = Compose(heroes.Select(h => h.Faction));
        double hp = heroes.Average(h => h.HealthContribution) * effect.HealthBonus;
        double offense = heroes.Average(h => Counters(h.Faction, enemyFaction) ? h.OffenseIndex * (.20 + effect.CounterBonus) : 0);
        bool flat = heroes[0].Estimate?.Basis == "Flat max stats";
        double dw = flat ? .25 : .35, ow = flat ? .35 : .55;
        return mode switch
        {
            PlannerMode.Offense => flat ? offense : .75 * offense + .25 * (ow * offense + dw * hp),
            PlannerMode.Survival => flat ? hp : .75 * hp + .25 * (ow * offense + dw * hp),
            PlannerMode.Pve when !flat => .45 * offense + .30 * hp + .25 * (ow * offense + dw * hp),
            _ => ow * offense + dw * hp,
        };
    }
}
