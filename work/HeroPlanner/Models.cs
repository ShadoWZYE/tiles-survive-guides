using System.Text.Json.Serialization;

namespace TilesSurviveHeroPlanner;

[Flags]
internal enum HeroMechanic
{
    None = 0,
    Summon = 1 << 0,
    Healing = 1 << 1,
    Shield = 1 << 2,
    Stun = 1 << 3,
    Slow = 1 << 4,
    AttackReduction = 1 << 5,
    DefenseReduction = 1 << 6,
    DamageReduction = 1 << 7,
    DamageBoost = 1 << 8,
    CriticalEffect = 1 << 9,
    StaminaReduction = 1 << 10,
}

public sealed class Hero
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("asset_slug")] public string AssetSlug { get; set; } = "";
    [JsonPropertyName("hero_id")] public int HeroId { get; set; }
    [JsonPropertyName("faction")] public string Faction { get; set; } = "";
    [JsonPropertyName("role")] public string Role { get; set; } = "";
    [JsonPropertyName("rarity")] public string Rarity { get; set; } = "";
    [JsonPropertyName("rarity_code")] public int RarityCode { get; set; }
    [JsonPropertyName("client_version")] public string ClientVersion { get; set; } = "";
    [JsonPropertyName("minimum_server_version")] public string MinimumServerVersion { get; set; } = "";
    [JsonPropertyName("release_week_min")] public int? ReleaseWeekMin { get; set; }
    [JsonPropertyName("release_week_max")] public int? ReleaseWeekMax { get; set; }
    [JsonPropertyName("has_ascension")] public bool HasAscension { get; set; }
    [JsonPropertyName("acquisition_class")] public string AcquisitionClass { get; set; } = "unknown";
    [JsonPropertyName("acquisition_label")] public string AcquisitionLabel { get; set; } = "Acquisition route unknown";
    [JsonPropertyName("acquisition_confidence")] public string AcquisitionConfidence { get; set; } = "low";
    [JsonPropertyName("recruit_pool")] public bool RecruitPool { get; set; }
    [JsonPropertyName("turntable_event")] public bool TurntableEvent { get; set; }
    [JsonPropertyName("iap_linked")] public bool IapLinked { get; set; }
    [JsonPropertyName("max_level_battle_power")] public double BattlePower { get; set; }
    [JsonPropertyName("max_level")] public int MaxLevel { get; set; }
    [JsonPropertyName("max_level_attack")] public double Attack { get; set; }
    [JsonPropertyName("max_level_defense")] public double Defense { get; set; }
    [JsonPropertyName("max_level_health")] public double Health { get; set; }
    [JsonPropertyName("max_level_march_capacity")] public double MarchCapacity { get; set; }
    [JsonPropertyName("offense_index")] public double OffenseIndex { get; set; }
    [JsonPropertyName("durability_index")] public double DurabilityIndex { get; set; }
    [JsonPropertyName("composite_index")] public double CompositeIndex { get; set; }
    [JsonPropertyName("skills")] public List<HeroSkill> Skills { get; set; } = [];

    [JsonIgnore] public bool IsSelected { get; set; }
    [JsonIgnore] public bool IsOwned { get; set; }
    [JsonIgnore] public HeroProgress Progress { get; set; } = new();
    [JsonIgnore] public string Portrait => $"pack://application:,,,/TilesSurviveHeroPlanner;component/Images/{AssetSlug}.png";
    [JsonIgnore] public string FormationBand => Role switch
    {
        "Melee" => "Frontline",
        "Mid" => "Midline",
        "Range" => "Backline",
        _ => "Flexible",
    };
    [JsonIgnore] public string ReleaseLabel => ReleaseWeekMin is null ? "Core roster" :
        ReleaseWeekMin == ReleaseWeekMax ? $"Week {ReleaseWeekMin}" : $"Weeks {ReleaseWeekMin}–{ReleaseWeekMax}";
    [JsonIgnore] public string ClientGateLabel => string.IsNullOrWhiteSpace(ClientVersion) ? "No client gate recorded" : $"Client {ClientVersion}+";
    [JsonIgnore] public string ServerGateLabel => string.IsNullOrWhiteSpace(MinimumServerVersion) ? "No minimum server build recorded" : $"Server {MinimumServerVersion}+";
    [JsonIgnore] public string AcquisitionEvidence => $"{AcquisitionLabel} • {AcquisitionConfidence} confidence";
    private double? _staminaReductionPercent;
    [JsonIgnore] public double StaminaReductionPercent => _staminaReductionPercent ??= Skills
            .SelectMany(skill => skill.MaxLevelOverallBenefits)
            .Where(benefit => benefit.Name.Equals("prop_intel_stamina_reduce_percent", StringComparison.OrdinalIgnoreCase))
            .Select(benefit => Math.Abs(benefit.Value) * 100)
            .DefaultIfEmpty(0)
            .Max();
    [JsonIgnore] public string PveUtilityLabel => StaminaReductionPercent > 0
        ? $"Global Stamina cost −{StaminaReductionPercent:0.#}%" : "No extracted Stamina economy effect";

    private HashSet<string>? _mechanicCache;
    private HeroMechanic? _mechanicFlags;
    [JsonIgnore] internal HeroMechanic MechanicFlags => _mechanicFlags ??= GetMechanicFlags();
    public bool HasMechanic(string mechanic)
    {
        _mechanicCache ??= Skills.SelectMany(skill =>
            skill.Mechanics.Split(" • ", StringSplitOptions.RemoveEmptyEntries)).ToHashSet(StringComparer.Ordinal);
        return _mechanicCache.Contains(mechanic);
    }

    private HeroMechanic GetMechanicFlags()
    {
        HeroMechanic flags = HeroMechanic.None;
        foreach (string mechanic in Skills.SelectMany(skill =>
                     skill.Mechanics.Split(" • ", StringSplitOptions.RemoveEmptyEntries)))
        {
            flags |= mechanic switch
            {
                "Summon" => HeroMechanic.Summon,
                "Healing" => HeroMechanic.Healing,
                "Shield" => HeroMechanic.Shield,
                "Stun" => HeroMechanic.Stun,
                "Slow" => HeroMechanic.Slow,
                "ATK reduction" => HeroMechanic.AttackReduction,
                "DEF reduction" => HeroMechanic.DefenseReduction,
                "Damage reduction" => HeroMechanic.DamageReduction,
                "Damage boost" => HeroMechanic.DamageBoost,
                "Critical effect" => HeroMechanic.CriticalEffect,
                "Stamina reduction" => HeroMechanic.StaminaReduction,
                _ => HeroMechanic.None,
            };
        }
        return flags;
    }
}

public sealed class HeroSkill
{
    [JsonPropertyName("internal_name")] public string InternalName { get; set; } = "";
    [JsonPropertyName("display_name")] public string LocalizedName { get; set; } = "";
    [JsonPropertyName("game_description")] public string GameDescription { get; set; } = "";
    [JsonPropertyName("icon_asset")] public string IconAsset { get; set; } = "";
    [JsonPropertyName("slot")] public int Slot { get; set; }
    [JsonPropertyName("normal_attack")] public bool NormalAttack { get; set; }
    [JsonPropertyName("damage_ratio")] public double DamageRatio { get; set; }
    [JsonPropertyName("damage_params")] public List<double> DamageParams { get; set; } = [];
    [JsonPropertyName("skill_value")] public int SkillValue { get; set; }
    [JsonPropertyName("effect_description_key")] public string EffectDescriptionKey { get; set; } = "";
    [JsonPropertyName("squad_parameter_map")] public string SquadParameterMap { get; set; } = "";
    [JsonPropertyName("raid_level_parameters")] public List<string> RaidLevelParameters { get; set; } = [];
    [JsonPropertyName("configured_max_level")] public int? ConfiguredMaxLevel { get; set; }
    [JsonPropertyName("max_level_overall_benefits")] public List<HeroBenefit> MaxLevelOverallBenefits { get; set; } = [];

    [JsonIgnore] public string DisplayName => !string.IsNullOrWhiteSpace(LocalizedName)
        ? LocalizedName : NormalAttack ? "Basic attack" : Slot > 0 ? $"Skill {Slot}" : HumanizeInternalName();
    [JsonIgnore] public string Icon => string.IsNullOrWhiteSpace(IconAsset) ? "" : $"pack://application:,,,/TilesSurviveHeroPlanner;component/Images/SkillIcons/{IconAsset}.png";
    [JsonIgnore] public string Description => string.IsNullOrWhiteSpace(GameDescription)
        ? "The English client has no squad description for this skill."
        : System.Text.RegularExpressions.Regex.Replace(GameDescription, @"\{(\d+)\}", "[runtime value $1]");
    [JsonIgnore] public string DamageLabel => "Runtime damage not simulated. Skill-level parameters are modifiers, not multiples of ATK.";
    [JsonIgnore] public string LevelLabel => ConfiguredMaxLevel is null ? "Level data unavailable" : $"Configured to level {ConfiguredMaxLevel}";
    [JsonIgnore] public string Mechanics => DescribeMechanics();
    [JsonIgnore] public string ExpectedPayoff => DescribePayoff();

    private string HumanizeInternalName()
    {
        int marker = InternalName.LastIndexOf("_skill_", StringComparison.OrdinalIgnoreCase);
        return marker >= 0 ? "Skill " + InternalName[(marker + 7)..].Replace('_', ' ') : InternalName.Replace('_', ' ');
    }

    private string DescribeMechanics()
    {
        string source = string.Join('|', RaidLevelParameters) + "|" + SquadParameterMap + "|" + GameDescription;
        var tags = new List<string>();
        void Add(string needle, string label)
        {
            if (source.Contains(needle, StringComparison.OrdinalIgnoreCase) && !tags.Contains(label)) tags.Add(label);
        }
        Add("summon", "Summon");
        Add("heal", "Healing");
        Add("shield", "Shield");
        Add("stun", "Stun");
        Add("speeddown", "Slow");
        Add("weaken_team_atk", "ATK reduction");
        Add("weaken_enemy_atk", "ATK reduction");
        Add("weaken_team_def", "DEF reduction");
        Add("weaken_enemy_def", "DEF reduction");
        Add("dmg_dec", "Damage reduction");
        Add("inc_dmg", "Damage boost");
        Add("crit", "Critical effect");
        Add("stamina", "Stamina reduction");
        Add("hpmax", "Maximum health");
        if (tags.Count == 0 && (NormalAttack || source.Contains("damage", StringComparison.OrdinalIgnoreCase))) tags.Add("Damage");
        return tags.Count == 0 ? "Mechanic not yet classified" : string.Join(" • ", tags);
    }

    private string DescribePayoff()
    {
        string mechanics = Mechanics;
        if (NormalAttack) return "Reliable basic damage; mostly a baseline rather than a reason to build the hero.";
        if (mechanics.Contains("Healing") && mechanics.Contains("Shield")) return "Strong sustain package: restores health and prevents follow-up damage.";
        if (mechanics.Contains("Healing")) return "Sustain value rises in longer fights and when the squad survives long enough for repeated casts.";
        if (mechanics.Contains("Shield") || mechanics.Contains("Damage reduction")) return "Protective value is highest for keeping fragile damage dealers active.";
        if (mechanics.Contains("Stun") || mechanics.Contains("Slow")) return "Control creates safer damage windows and reduces incoming pressure; payoff depends on effect uptime.";
        if (mechanics.Contains("ATK reduction") || mechanics.Contains("DEF reduction")) return "Team utility: weakens enemies so the whole squad either takes less damage or deals more.";
        if (mechanics.Contains("Stamina reduction"))
        {
            double reduction = MaxLevelOverallBenefits
                .Where(benefit => benefit.Name.Equals("prop_intel_stamina_reduce_percent", StringComparison.OrdinalIgnoreCase))
                .Select(benefit => Math.Abs(benefit.Value) * 100).DefaultIfEmpty(0).Max();
            return reduction > 0
                ? $"Global PvE economy: the extracted maximum benefit reduces Stamina consumption by {reduction:0.#}%, allowing more farming from the same daily resource."
                : "Global PvE economy: lowers Stamina spent per action, allowing more farming from the same daily resource.";
        }
        if (mechanics.Contains("Summon")) return "Adds another battlefield source of pressure; practical value depends on summon uptime and survivability.";
        return "The client exposes this effect, but its practical payoff needs a fuller battle-effect simulation.";
    }
}

public sealed class HeroBenefit
{
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("value")] public double Value { get; set; }
}

public enum PlannerMode
{
    Balanced,
    Offense,
    Survival,
    Pve
}

public sealed class SquadResult
{
    public required IReadOnlyList<Hero> Heroes { get; init; }
    public required double Score { get; init; }
    public required string Label { get; init; }
    public double BaseScore { get; init; }
    public double SynergyBonus { get; init; }
    public string SynergySummary { get; init; } = "No modeled cross-skill pairing";
    public string Names => string.Join(" • ", Heroes.Select(hero => hero.Name));
    public string SynergyLabel => SynergyBonus > 0 ? $"+{SynergyBonus:0.0} synergy" : "No synergy bonus";
}

public sealed class ReleaseScheduleItem
{
    public required string Marker { get; init; }
    public required string HeroName { get; init; }
    public required string WeekLabel { get; init; }
    public required string DateLabel { get; init; }
    public required string RelativeLabel { get; init; }
}

public sealed class PlannerProfile
{
    [JsonPropertyName("hero_builds")] public Dictionary<string, HeroBuild> HeroBuilds { get; set; } = [];
    [JsonPropertyName("upgrade_settings")] public UpgradeSettings UpgradeSettings { get; set; } = new();
    [JsonPropertyName("hero_progress")] public Dictionary<string, HeroProgress> HeroProgress { get; set; } = [];
    [JsonPropertyName("owned_heroes")] public HashSet<string> OwnedHeroes { get; set; } = [];
    [JsonPropertyName("server_open_date")] public DateTime? ServerOpenDate { get; set; }
}
