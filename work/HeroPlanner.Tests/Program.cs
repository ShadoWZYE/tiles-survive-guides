using System.Text.Json;
using TilesSurviveHeroPlanner;

if(args.Length==2 && args[0]=="--recorded-scores")
{
 var root=args[1];var data=UpgradeData.Parse(File.ReadAllText(Path.Combine(root,"TilesSurvive-Upgrade-Data.json")));var model=EstimateData.Parse(File.ReadAllText(Path.Combine(root,"Hero-Estimate-Model.json")));var recordedCases=new List<object>();
 foreach(var (slug,h) in data.Heroes){var stage=h.Stages.First();var complete=new HeroBuild{Stage=stage.Id,Level=1,Gear=[],Skills=h.Skills.ToDictionary(s=>s.Id,s=>stage.SkillCaps.ElementAtOrDefault(s.Slot)>0?1:0)};var unknownGear=complete.Copy();unknownGear.Gear=null;var missingLevel=complete.Copy();missingLevel.Level=null;var missingSkill=complete.Copy();missingSkill.Skills.Clear();foreach(var saved in new HeroBuild?[]{null,complete,unknownGear,missingLevel,missingSkill})recordedCases.Add(new{slug,saved,result=EstimateModel.Evaluate(slug,saved,data,model,0,null,true)});}
 Console.WriteLine(JsonSerializer.Serialize(recordedCases,new JsonSerializerOptions{PropertyNamingPolicy=JsonNamingPolicy.CamelCase}));return;
}

if(args.Length==2 && args[0]=="--army-context")
{
 var root=args[1];var data=ArmyContextData.Parse(File.ReadAllText(Path.Combine(root,"Hero-Army-Context.json")));
 var estimates=EstimateData.Parse(File.ReadAllText(Path.Combine(root,"Hero-Estimate-Model.json")));
 var upgrades=UpgradeData.Parse(File.ReadAllText(Path.Combine(root,"TilesSurvive-Upgrade-Data.json")));
 var armyCases=new List<object>();
 var contexts=new ArmyContextSettings[]{new(){Enabled=true,BehemothSource="configured",Behemoth=[999,999,999],BehemothBuilds=new(){{"caser",new(){Level=1,Star=1}}}},new(){Enabled=true,BehemothSource="configured",BehemothBuilds=new(){{"caser",new(){Level=99999,Star=1}},{"missing",new(){Level=1,Star=1}}}},new(),new(){Enabled=true},new(){Enabled=true,Behemoth=[348,70,23184]},new(){Enabled=true,Scene="pve",Research=data.Research.ToDictionary(x=>x.Key,x=>x.Value.Levels.Last().Level)},new(){Enabled=true,Signature=data.Signature.ToDictionary(x=>x.Key,x=>x.Value.Levels.First().Level)},new(){Enabled=true,Scene="gve",Behemoth=[null,200,5000],Research=data.Research.Take(5).ToDictionary(x=>x.Key,x=>x.Value.Levels.Last().Level),Signature=new(){{"rosie",1},{"missing",999}}}};
 foreach(var settings in contexts)foreach(string basis in new[]{"reference","recorded","flat"})foreach(var slug in estimates.Heroes.Keys)
 {
  var context=ArmyContextModel.Resolve(slug,settings,data,basis);
  var result=EstimateModel.Evaluate(slug,null,upgrades,estimates,20,context.Flat);
  armyCases.Add(new{slug,basis,settings,context,result=new{result.Offense,result.Durability,result.Score,result.HealthContribution,result.PassiveContributions}});
 }
 Console.WriteLine(JsonSerializer.Serialize(armyCases,new JsonSerializerOptions{PropertyNamingPolicy=JsonNamingPolicy.CamelCase}));return;
}

if (args.Contains("--formation-fit"))
{
    var fitCases = new List<object>();
    for (int n = 0; n < 64; n++)
    foreach (bool flat in new[] { false, true })
    foreach (var mode in Enum.GetValues<PlannerMode>())
    foreach (double health in new[] { 0.0, .12, .25 })
    {
        var fitHeroes = Enumerable.Range(0, 5).Select(i => new Hero {
            AssetSlug = $"hero-{i}", Name = $"Hero {i}",
            Role = n % 4 == 0 ? "Range" : new[] { "Melee", "Mid", "Range" }[(n + i) % 3],
            OffenseIndex = 40 + (n * 3 + i * 13) % 110,
            DurabilityIndex = n == 0 ? 0 : n == 1 ? 100 : 20 + (n * 11 + i * 31) % 130,
            HealthContribution = n == 1 ? 60 : 10 + i * 7,
            Estimate = new(0, 0, 0, 0, 0, flat ? "Flat max stats" : "Reference build",0,
                [40+i*3,12+i*2,20+i*4],[i==0 ? .12 : 0,i==1 ? .1 : 0,i==2 ? .04 : 0])
        }).ToArray();
        var result = FormationModel.Evaluate(fitHeroes, mode, health);
        fitCases.Add(new { heroes = fitHeroes.Select(h => new { asset_slug = h.AssetSlug, role = h.Role, offense_index = h.OffenseIndex, durability_index = h.DurabilityIndex, healthContribution = h.HealthContribution,estimate = h.Estimate }), flat, mode = mode == PlannerMode.Pve ? "PvE farming" : mode.ToString(), health,
            order = result.Heroes.Select(h => h.AssetSlug), result.Adjustment, result.FrontDurability,passiveBonus=FormationModel.PassiveBonus(fitHeroes,mode) });
    }
    Console.WriteLine(JsonSerializer.Serialize(fitCases, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
    return;
}

if (args.Contains("--factions"))
{
    string[] factions = ["Mountain", "Wasteland", "Sky", "Sea"];
    string[] enemies = ["Unknown", "Mountain", "Wasteland", "Sky", "Sea"];
    var factionCases = new List<object>();
    for (int n = 0; n < 1024; n++)
    {
        int code = n;
        var lineup = new List<Hero>();
        for (int i = 0; i < 5; i++, code /= 4)
            lineup.Add(new Hero { Faction = factions[code % 4], HealthContribution = 80 + i, OffenseIndex = 100 + i });
        var effect = FactionModel.Compose(lineup.Select(h => h.Faction));
        var scores = new List<double>();
        foreach (bool flat in new[] { false, true })
        {
            foreach (var h in lineup) h.Estimate = new(100, 100, 100, 100, 100, flat ? "Flat max stats" : "Reference build");
            foreach (var mode in Enum.GetValues<PlannerMode>())
            foreach (string enemy in enemies) scores.Add(FactionModel.ScoreBonus(lineup, mode, enemy));
        }
        factionCases.Add(new { factions = lineup.Select(h => h.Faction), effect, scores });
    }
    Console.WriteLine(JsonSerializer.Serialize(factionCases, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
    return;
}

if (args.Length > 2 && args[1] == "--estimates")
{
    var basicScenario=new EstimateSkill {Id="basic",Slot=0,Priority=0,QueueEligible=true,CastDurationAtUnitSpeedSeconds=2,CadenceAssumedSeconds=2};
    var activeScenario=new EstimateSkill {Id="active",Slot=1,Priority=3,QueueEligible=true,BasePreCooldownMs=1000,CastDurationAtUnitSpeedSeconds=3,CadenceAssumedSeconds=6};
    var scheduleScenario=EstimateModel.OpeningSchedule([basicScenario,activeScenario],8);
    if(!scheduleScenario["basic"].SequenceEqual(new double[]{2,7}) || !scheduleScenario["active"].SequenceEqual(new double[]{5}) || EstimateModel.CoveredTime([2,4,8],4,10)!=8)
        throw new Exception("Shared casting slot failed the hand-calculated scenario");
    var timedBudget=new EstimateCastBudget {DirectCoefficient=6,DirectEvents=[new(){OffsetSeconds=.5,Coefficient=2},new(){OffsetSeconds=1.5,Coefficient=4}]};
    if(EstimateModel.OpeningDamage(timedBudget,[2],2,1)!=2 || EstimateModel.OpeningSchedule([basicScenario],1,true)["basic"].Single()!=2)
        throw new Exception("Partial-cast dispatch timing failed the hand-calculated scenario");
    var root = args[2]; var upgrades = UpgradeData.Parse(File.ReadAllText(Path.Combine(root, "TilesSurvive-Upgrade-Data.json")));
    var estimates = EstimateData.Parse(File.ReadAllText(Path.Combine(root, "Hero-Estimate-Model.json")));
    var finishScenario=new EstimateFinishTrigger {SourceSkillId="active",CooldownSeconds=5,DelaySeconds=0};
    if(!EstimateModel.FinishTriggers(finishScenario,[2,4,8,10],10).SequenceEqual(new double[]{2,8}))
        throw new Exception("Finish trigger cooldown and final-update boundary failed");
    foreach(int window in new[]{0,10,20,30})
    {
        var parentLocked=new HeroBuild {Skills=new() {{"survivor_ray_skill_1",0}}};
        var bothLocked=new HeroBuild {Skills=new() {{"survivor_ray_skill_1",0},{"survivor_ray_skill_2",0}}};
        if(Math.Abs(EstimateModel.Evaluate("ray",parentLocked,upgrades,estimates,window).Score-EstimateModel.Evaluate("ray",bothLocked,upgrades,estimates,window).Score)>1e-9)
            throw new Exception("Ray passive contributed with its source active locked");
        if(!EstimateModel.Evaluate("ray",parentLocked,upgrades,estimates,window).ActiveSkillIds!.SequenceEqual(EstimateModel.Evaluate("ray",bothLocked,upgrades,estimates,window).ActiveSkillIds!))
            throw new Exception("Ray passive supplied squad synergy with its source active locked");
    }
    var estimateCases = new List<object>();
    foreach (var slug in estimates.Heroes.Keys)
    {
        var h = upgrades.Heroes[slug]; var model = estimates.Heroes[slug];
        HeroBuild?[] builds = [null, new() { Stage = model.ReferenceStage, Level = model.ReferenceLevel, Gear = [], Skills = model.Skills.ToDictionary(s => s.Id, s => s.ReferenceLevel) },
            new() { Stage = h.Stages[0].Id, Level = 1, Skills = h.Skills.ToDictionary(s => s.Id, s => 0) }, new() { Level = 55 }];
        foreach (var saved in builds)
        foreach (int battleSeconds in new[] {0,10,20,30})
            estimateCases.Add(new { slug, saved, battleSeconds, result = EstimateModel.Evaluate(slug, saved, upgrades, estimates, battleSeconds) });
    }
    Console.WriteLine(JsonSerializer.Serialize(estimateCases, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
    return;
}

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
var legacyCarries = FormationPriority.Carries(example);
Check(FormationPriority.Rank(example, PlannerMode.Balanced)[0].Hero == legacyCarries[0], "Primary damage core was ignored");
Check(FormationPriority.Rank(example, PlannerMode.Balanced)[1].Hero.Role == "Melee", "Frontline priority was ignored");
Check(FormationPriority.Rank(example, PlannerMode.Offense).Take(2).Select(x => x.Hero).SequenceEqual(legacyCarries), "Offense core order disagrees");
Check(FormationPriority.Rank(example, PlannerMode.Survival)[0].Hero.Role == "Melee", "Survival must start with frontline priority");
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
