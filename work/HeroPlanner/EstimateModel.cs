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
    public string DamageSelectionBasis { get; set; } = "";
    public bool HasDamageZone { get; set; }
    public bool HasSummonDependency { get; set; }
    public List<EstimateStatSource> PermanentStatSources { get; set; } = [];
    public List<string> SequenceEffectIds { get; set; } = [];
    public List<EstimateTimedStatSource> TemporaryStatSources { get; set; } = [];
    public List<EstimatePeriodicBudget> PeriodicBudgets { get; set; } = [];
    public List<EstimateConditionalEffect> ConditionalEffects { get; set; } = [];
    public bool AnimationLimited { get; set; }
    public Dictionary<string,int> DirectHitCounts { get; set; } = [];
    public bool QueueEligible { get; set; }
    public int Priority { get; set; }
    public int BasePreCooldownMs { get; set; }
    public double CadenceAssumedSeconds { get; set; }
    public double? CastDurationAtUnitSpeedSeconds { get; set; }
    public EstimateFinishTrigger? FinishTrigger { get; set; }
}
public sealed class EstimateFinishTrigger { public string SourceSkillId { get; set; } = ""; public double CooldownSeconds { get; set; } public double DelaySeconds { get; set; } }
public sealed class EstimateConditionalEffect { public string Id { get; set; } = ""; public int ConditionId { get; set; } }
public sealed class EstimateTimedStatSource { public string Id { get; set; } = ""; public double AssumedUptime { get; set; } }
public sealed class EstimatePeriodicBudget { public string EffectId { get; set; } = ""; public int NominalTicks { get; set; } public bool Scored { get; set; } }
public sealed class EstimateStatSource { public string Id { get; set; } = ""; public string Scope { get; set; } = ""; }
public sealed class EstimateSkillLevel
{
    public int Level { get; set; }
    public double Damage { get; set; }
    public double Utility { get; set; }
    public double[] SelfPercent { get; set; } = [0,0,0];
    public double[] TeamPercent { get; set; } = [0,0,0];
    public Dictionary<string,EstimateOpeningWindow> OpeningWindows { get; set; } = [];
    public EstimateCastBudget? CastBudget { get; set; }
    public List<EstimateHealingBudget> HealingBudgets { get; set; } = [];
}
public sealed class EstimateHealingBudget
{
    public double AttackCoefficient { get; set; }
    public double FlatAmount { get; set; }
    public List<EstimateHealingTerm> PropertyTerms { get; set; } = [];
    public string Execution { get; set; } = "";
}
public sealed class EstimateHealingTerm { public string Owner { get; set; } = ""; public string Property { get; set; } = ""; public double Coefficient { get; set; } }
public sealed record HealingPreview(string SkillId,string Formula,string Execution);
public sealed class EstimateCastBudget
{
    public double DirectCoefficient { get; set; }
    public List<EstimateTimedDamage> DirectEvents { get; set; } = [];
    public List<EstimateTickBudget> PeriodicTicks { get; set; } = [];
    public double[] PermanentSelfPercent { get; set; } = [0,0,0];
    public List<EstimateTemporaryBuff> TemporaryBuffs { get; set; } = [];
}
public sealed class EstimateTimedDamage { public double OffsetSeconds { get; set; } public double Coefficient { get; set; } }
public sealed class EstimateTickBudget { public int NominalTicks { get; set; } public int IntervalMs { get; set; } public double CoefficientPerTick { get; set; } public double? ApplicationOffsetSeconds { get; set; } }
public sealed class EstimateTemporaryBuff { public double DurationSeconds { get; set; } public double[] Percent { get; set; } = [0,0,0]; public double? ApplicationOffsetSeconds { get; set; } }
public sealed class EstimateOpeningWindow
{
    public double Damage { get; set; }
    public double[] SelfPercent { get; set; } = [0,0,0];
}
public sealed record HeroEstimate(double Offense, double Durability, double Score, double Low, double High, string Basis, double HealthContribution = 0,
    double[]? PassiveContributions = null, double[]? TeamPercent = null, double[]? SelfPercent = null, string[]? ActiveSkillIds = null,
    Dictionary<string,int>? OpeningCastCounts = null,List<HealingPreview>? RawHealingPotential = null, bool Comparable = true, string[]? MissingFields = null);

public static class EstimateModel
{
    public static string HealingFormula(EstimateHealingBudget budget)
    {
        static string Number(double value)=>value.ToString("0.#######",System.Globalization.CultureInfo.InvariantCulture);
        var terms=new List<string>();
        if(budget.AttackCoefficient>0)terms.Add($"{Number(budget.AttackCoefficient)} x caster ATK");
        if(budget.FlatAmount>0)terms.Add(Number(budget.FlatAmount));
        terms.AddRange(budget.PropertyTerms.Where(t=>t.Coefficient>0).Select(t=>$"{Number(t.Coefficient)} x {t.Owner} {t.Property}"));
        return string.Join(" + ",terms);
    }
    // Explicit non-preemptive scenario, not the full native interrupt/AI scheduler.
    public static Dictionary<string,List<double>> OpeningSchedule(IEnumerable<EstimateSkill> source, int window, bool includeInFlight=false)
    {
        var skills=source.Where(s=>s.QueueEligible && s.CastDurationAtUnitSpeedSeconds is >0 && s.CadenceAssumedSeconds>0).ToArray();
        var completed=skills.ToDictionary(s=>s.Id,_=>new List<double>());
        var ready=skills.ToDictionary(s=>s.Id,s=>s.BasePreCooldownMs/1000.0);
        double time=0;
        for(int guard=0;skills.Length>0 && time<=window && guard<10000;guard++)
        {
            var next=skills.Where(s=>ready[s.Id]<=time+1e-9).OrderByDescending(s=>s.Priority).ThenBy(s=>s.Slot).ThenBy(s=>s.Id,StringComparer.Ordinal).FirstOrDefault();
            if(next is null) {time=ready.Values.Min();continue;}
            double end=time+next.CastDurationAtUnitSpeedSeconds!.Value;
            if(end>window+1e-9) {if(includeInFlight)completed[next.Id].Add(end);break;}
            completed[next.Id].Add(end);
            ready[next.Id]=time+next.CadenceAssumedSeconds;
            time=end;
        }
        return completed;
    }
    public static double OpeningDamage(EstimateCastBudget budget,IEnumerable<double> ends,double duration,int window)
    {
        double total=0;
        foreach(double end in ends)
        {
            double start=end-duration;
            if(budget.DirectEvents.Count>0)
                total+=budget.DirectEvents.Where(e=>start+e.OffsetSeconds<=window+1e-9).Sum(e=>e.Coefficient);
            else if(end<=window+1e-9)total+=budget.DirectCoefficient;
            foreach(var tick in budget.PeriodicTicks)
            {
                double applied=start+(tick.ApplicationOffsetSeconds??duration);
                total+=Math.Min(tick.NominalTicks,Math.Max(0,Math.Floor((window-applied)*1000/tick.IntervalMs+1e-9)))*tick.CoefficientPerTick;
            }
        }
        return total/window;
    }
    public static double CoveredTime(IEnumerable<double> completions,double duration,int window)
    {
        double end=0,covered=0;
        foreach(double start in completions)
        {
            double stop=Math.Min(window,start+duration);
            covered+=Math.Max(0,stop-Math.Max(start,end));end=Math.Max(end,stop);
        }
        return covered;
    }
    public static List<double> FinishTriggers(EstimateFinishTrigger trigger,IEnumerable<double> ends,int window,double initialDelay=0)
    {
        double ready=initialDelay;var result=new List<double>();
        foreach(double end in ends)
        {
            if(end<ready-1e-9 || end+trigger.DelaySeconds>=window-1e-9)continue;
            result.Add(end+trigger.DelaySeconds);ready=end+trigger.CooldownSeconds;
        }
        return result;
    }
    public static string EvidenceSummary(EstimateHero model) =>
        $"Skill evidence: {model.Skills.Count(s => s.DamageSelectionBasis == "direct_hit_reference")} skills have linked direct damage effects; " +
        $"{model.Skills.Count(s => s.HasDamageZone)} have damage zones; {model.Skills.Count(s => s.HasSummonDependency)} have summon dependencies. " +
        $"{model.Skills.Sum(s => s.PermanentStatSources.Count)} permanent stat buffs are modeled; {model.Skills.Sum(s => s.SequenceEffectIds.Count)} checked child strikes are included. " +
        $"{model.Skills.Sum(s => s.TemporaryStatSources.Count)} temporary self stat buffs use assumed duration/cooldown uptime; {model.Skills.Sum(s => s.PeriodicBudgets.Count(p => p.Scored))} periodic damage paths use full-lifetime potential. " +
        $"{model.Skills.Sum(s => s.ConditionalEffects.Count)} effect gates are retained separately; description rows give no damage credit. " +
        $"{model.Skills.Count(s => s.FinishTrigger is not null)} delayed damage paths require a completed source skill and an unlocked passive. " +
        $"{model.Skills.Count(s => s.AnimationLimited)} skill budgets are limited by bound clip durations; {model.Skills.Count(s => s.DirectHitCounts.Values.Sum() > 1)} use repeated immediate-hit potential. " +
        "Timing assumes speed 1 and uninterrupted casting. Opening scenarios use known timeline dispatch offsets; unknown impacts keep a completion fallback. Projectile travel, target survival, reapplication timing, zones and death times remain uncertain.";
    public static List<string> MissingBuild(string slug, HeroBuild? saved, UpgradeData data)
    {
        var h=data.Heroes[slug];List<string> missing=[];var stage=h.Stages.Find(s=>s.Id==saved?.Stage);
        if(stage is null)missing.Add("exact rank / step");
        var level=h.Levels.Find(l=>l.Level==saved?.Level);if(level is null||stage is not null&&level.Level>stage.LevelMax)missing.Add("valid hero level");
        if(saved?.Gear is null)missing.Add("gear (record equipped items or explicitly none)");
        else{HashSet<int> slots=[];foreach(var g in saved.Gear)if(g is null||!data.Gear.TryGetValue(g.Id,out var type)||!type.Levels.Any(r=>r.Level==g.Level)||level is null||type.HeroLevelRequired>level.Level||!slots.Add(type.Slot)){missing.Add("valid gear slots / levels");break;}}
        if(stage is not null)foreach(var skill in h.Skills){int cap=stage.SkillCaps.ElementAtOrDefault(skill.Slot);if(cap==0)continue;if(saved?.Skills is null||!saved.Skills.TryGetValue(skill.Id,out int n)||n<0||n>cap||n>0&&!skill.Levels.Any(r=>r.Level==n))missing.Add(skill.Name+" level");}
        return missing;
    }
    public static HeroEstimate Evaluate(string slug, HeroBuild? saved, UpgradeData upgrades, EstimateData estimates, int battleSeconds = 0, double[]? externalFlat = null, bool requireRecorded = false)
    {
        if(requireRecorded){var missing=MissingBuild(slug,saved,upgrades);if(missing.Count>0)return new(0,0,0,0,0,"Incomplete build",Comparable:false,MissingFields:missing.ToArray());saved=saved!.Copy();var lockedStage=upgrades.Heroes[slug].Stages.Single(s=>s.Id==saved.Stage);foreach(var skill in upgrades.Heroes[slug].Skills)if(lockedStage.SkillCaps.ElementAtOrDefault(skill.Slot)==0)saved.Skills[skill.Id]=0;}
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
        double[] selfPercent = [0,0,0], teamPercent = [0,0,0];
        var activeSkills = new List<string>();
        var selected=new List<(EstimateSkill Skill,EstimateSkillLevel Row)>();
        foreach (var skill in model.Skills)
        {
            int cap = stage.SkillCaps.ElementAtOrDefault(skill.Slot);
            int skillLevel = Math.Min(skill.ReferenceLevel, cap);
            if (saved?.Skills is not null && saved.Skills.TryGetValue(skill.Id, out int recorded) && recorded >= 0 && recorded <= cap && skill.Levels.Any(l => l.Level == recorded))
            { skillLevel = recorded; known++; }
            var row = skill.Levels.Find(l => l.Level == skillLevel) ?? skill.Levels[0];
            if (row.Level > 0) activeSkills.Add(skill.Id);
            if (row.Level > 0) selected.Add((skill,row));
            var opening = battleSeconds is 10 or 20 or 30 ? row.OpeningWindows.GetValueOrDefault(battleSeconds.ToString()) : null;
            damage += opening?.Damage ?? row.Damage; utility += row.Utility;
            for(int i=0;i<3;i++) { selfPercent[i] += (opening?.SelfPercent ?? row.SelfPercent).ElementAtOrDefault(i); teamPercent[i] += row.TeamPercent.ElementAtOrDefault(i); }
        }
        var schedule=battleSeconds is 10 or 20 or 30 ? OpeningSchedule(selected.Where(x=>x.Row.CastBudget is not null).Select(x=>x.Skill),battleSeconds,true) : new();
        foreach(var (skill,row) in selected.Where(x=>schedule.ContainsKey(x.Skill.Id)))
        {
            var completions=schedule[skill.Id];var budget=row.CastBudget!;
            var independent=row.OpeningWindows.GetValueOrDefault(battleSeconds.ToString());
            double duration=skill.CastDurationAtUnitSpeedSeconds!.Value;
            damage+=OpeningDamage(budget,completions,duration,battleSeconds)-(independent?.Damage??row.Damage);
            var scheduledSelf=budget.PermanentSelfPercent.ToArray();
            foreach(var buff in budget.TemporaryBuffs)
                for(int i=0;i<3;i++)scheduledSelf[i]+=buff.Percent[i]*CoveredTime(completions.Select(end=>end-duration+(buff.ApplicationOffsetSeconds??duration)),buff.DurationSeconds,battleSeconds)/battleSeconds;
            for(int i=0;i<3;i++)selfPercent[i]+=scheduledSelf[i]-(independent?.SelfPercent??row.SelfPercent)[i];
        }
        foreach(var (skill,row) in selected.Where(x=>x.Skill.FinishTrigger is not null))
        {
            var trigger=skill.FinishTrigger!;
            bool parent=selected.Any(x=>x.Skill.Id==trigger.SourceSkillId),finite=battleSeconds is 10 or 20 or 30;
            double old=finite?(row.OpeningWindows.GetValueOrDefault(battleSeconds.ToString())?.Damage??row.Damage):row.Damage;
            double rate=!parent?0:finite?FinishTriggers(trigger,schedule.GetValueOrDefault(trigger.SourceSkillId)??[],battleSeconds,skill.BasePreCooldownMs/1000.0).Count*row.CastBudget!.DirectCoefficient/battleSeconds:row.Damage;
            damage+=rate-old;if(!parent){utility-=row.Utility;activeSkills.Remove(skill.Id);}
        }
        // External flat hero stats enter before in-battle passive stat modifiers.
        for(int i=0;i<3;i++) if(externalFlat?.ElementAtOrDefault(i) is double v && double.IsFinite(v) && v>=0)stats[i]+=v;
        var baseStats = stats.ToArray();
        var factors = Enumerable.Range(0,3).Select(i => 1+selfPercent[i]+teamPercent[i]).ToArray();
        for(int i=0;i<3;i++) stats[i] *= factors[i];
        (double offense, double durability, double score) Calculate(double damageFactor, double utilityFactor)
        {
            double o = 100 * stats[0] * (1 + .5 * Math.Log(1 + damage * damageFactor)) / estimates.Scales[0];
            double d = 100 * (.7 * stats[2] + 30 * stats[1]) / estimates.Scales[1];
            double u = 100 * (1 + utility * utilityFactor) / estimates.Scales[2];
            return (o, d, .55 * o + .35 * d + .1 * u);
        }
        var typical = Calculate(1, 1);
        return new(typical.offense, typical.durability, typical.score, Calculate(.5, .5).score, Calculate(2.5, 1.5).score,
            known == 0 ? "Reference build" : known == model.Skills.Count + 3 ? "Recorded build" : "Recorded + assumed",
            typical.durability * (.7 * stats[2]) / (.7 * stats[2] + 30 * stats[1]),
            [typical.offense/factors[0],typical.durability*30*baseStats[1]/(.7*stats[2]+30*stats[1]),typical.durability*.7*baseStats[2]/(.7*stats[2]+30*stats[1])],teamPercent,selfPercent,activeSkills.ToArray(),schedule.ToDictionary(x=>x.Key,x=>x.Value.Count(end=>end<=battleSeconds+1e-9)),
            selected.Where(x=>activeSkills.Contains(x.Skill.Id)).SelectMany(x=>x.Row.HealingBudgets.Select(b=>new HealingPreview(x.Skill.Id,HealingFormula(b),b.Execution))).ToList());
    }
}
