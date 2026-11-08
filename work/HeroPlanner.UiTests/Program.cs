using System.Reflection;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using TilesSurviveHeroPlanner;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        var scratch = Path.Combine(Path.GetTempPath(), "TilesPlannerUiTests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(scratch);
        string profilePath = Path.Combine(scratch, "profile.json");
        File.WriteAllText(profilePath, "{\"owned_heroes\":[\"becca\"]}");
        var app = new App { ShutdownMode=ShutdownMode.OnExplicitShutdown, IsolatedTestWindows=true };
        app.InitializeComponent();
        MainWindow Create() => (MainWindow)Activator.CreateInstance(typeof(MainWindow),
            BindingFlags.Instance | BindingFlags.NonPublic, null, [profilePath], null)!;
        void Invoke(MainWindow window, string method, params object[] args)
        {
            foreach (var e in args.OfType<RoutedEventArgs>()) e.RoutedEvent ??= Button.ClickEvent;
            typeof(MainWindow).GetMethod(method, BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, args);
        }
        void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
        T Field<T>(MainWindow window, string name) => (T)typeof(MainWindow).GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!;
        var window = Create(); // Exercises XAML initialization and both mode-picker event handlers.
        var heroes = (List<Hero>)typeof(MainWindow).GetField("_heroes", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!;
        var becca = heroes.Single(h => h.Name == "Becca");
        Check(heroes.All(h => h.Estimate is not null && double.IsFinite(h.Estimate.Score)), "Missing default hero estimate");
        Check(heroes.Single(h=>h.AssetSlug=="ken").CombatEvidenceNote.Contains("x caster HP"),"Chef raw healing source is not inspectable");
        Check(heroes.Single(h=>h.AssetSlug=="maddie").CombatEvidenceNote.Contains("x recipient HP"),"Frank recipient-based raw healing source is not inspectable");
        Check(heroes.Single(h=>h.AssetSlug=="maddie").CombatEvidenceNote.Contains("before modifiers and overheal; informational only"),"Raw healing scope is not explicit");
        var timingPicker = Field<ComboBox>(window,"BattleWindowPicker");
        var sustainedNikola = heroes.Single(h=>h.AssetSlug=="nikola").OffenseIndex;
        timingPicker.SelectedItem=timingPicker.Items.Cast<ComboBoxItem>().Single(i=>(string)i.Tag=="10");
        Check(heroes.Single(h=>h.AssetSlug=="nikola").OffenseIndex<sustainedNikola,"Opening window did not recompute estimates");
        Check(heroes.Single(h=>h.AssetSlug=="nikola").CombatEvidenceNote.Contains("Completed casts:"),"Opening cast counts are not inspectable");
        using(var timingSave=JsonDocument.Parse(File.ReadAllText(profilePath)))
            Check(timingSave.RootElement.GetProperty("battle_seconds").GetInt32()==10,"Opening window did not persist");
        timingPicker.SelectedItem=timingPicker.Items.Cast<ComboBoxItem>().Single(i=>(string)i.Tag=="0");
        Check(Math.Abs(heroes.Single(h=>h.AssetSlug=="nikola").OffenseIndex-sustainedNikola)<1e-8,"Sustained scores did not restore");
        Check(heroes.Where(h => h.Rarity == "SSR").Select(h => Math.Round(h.CompositeIndex, 3)).Distinct().Count() > 5, "SSR reference estimates collapsed into ties");
        var synergyMethod = typeof(MainWindow).GetMethod("EvaluateSynergy", BindingFlags.Static | BindingFlags.NonPublic)!;
        var healer = new Hero { Name="Healer", Skills=[new() { InternalName="heal", GameDescription="heal" }],
            Estimate=new(100,100,100,100,100,"Recorded build",ActiveSkillIds:["heal"]) };
        var protector = new Hero { Name="Protector", Skills=[new() { InternalName="shield", GameDescription="shield" }],
            Estimate=new(100,100,100,100,100,"Recorded build",ActiveSkillIds:["shield"]) };
        (double Bonus,string Summary) Synergy() => ((double,string))synergyMethod.Invoke(null,[new List<Hero>{healer,protector},PlannerMode.Balanced,true])!;
        Check(healer.HasMechanic("Healing") && Synergy().Bonus==0,"Trait presence added duplicate utility credit");
        healer.Estimate=healer.Estimate! with { ActiveSkillIds=[] };
        Check(!healer.HasMechanic("Healing") && Synergy().Bonus==0,"Locked healing still receives synergy or stale cached tags");
        healer.Estimate=healer.Estimate! with { ActiveSkillIds=["heal"] };
        Check(healer.HasMechanic("Healing") && Synergy().Bonus==0,"Re-unlocked healing added duplicate utility credit");
        var economyHero = new Hero { OffenseIndex=100,DurabilityIndex=100,CompositeIndex=100,
            Skills=[new() { MaxLevelOverallBenefits=[new() { Name="prop_intel_stamina_reduce_percent",Value=-.3 }] }] };
        var scoreMethod=typeof(MainWindow).GetMethod("ScoreHero",BindingFlags.Static|BindingFlags.NonPublic)!;
        Check(Math.Abs((double)scoreMethod.Invoke(null,[economyHero,PlannerMode.Pve])!-100)<1e-9,
            "Stamina economy inflated PvE combat strength");
        var synthetic = new[] { "Mountain", "Mountain", "Mountain", "Mountain", "Sea", "Wasteland" }
            .Select((f, i) => new Hero { Name = $"Test{i}", AssetSlug = $"test{i}", Faction = f,
                OffenseIndex = 100, DurabilityIndex = 100, CompositeIndex = 100, HealthContribution = 80,
                Estimate = new(100, 100, 100, 100, 100, "Reference build") }).ToList();
        var optimize = typeof(MainWindow).GetMethod("FindTopSquads", BindingFlags.Static | BindingFlags.NonPublic)!;
        var regressionData=Field<UpgradeData>(window,"_upgradeData");
        var regressionModel=Field<EstimateData>(window,"_estimates");
        var regressionStage=regressionData.Heroes["freja"].Stages.Single(s=>s.Id=="survivor_freja_rank_9_2");
        var regressionBuild=new HeroBuild{Stage=regressionStage.Id,Level=120,Gear=[],Skills=regressionData.Heroes["freja"].Skills.ToDictionary(s=>s.Id,s=>Math.Min(10,regressionStage.SkillCaps[s.Slot]))};
        regressionBuild.Skills.Remove("survivor_freja_skill_3");
        var regressionEstimate=EstimateModel.Evaluate("freja",regressionBuild,regressionData,regressionModel,0,null,true);
        var regressionFreja=new Hero{Name="Freja",AssetSlug="freja",Role="Mid",Faction="Wasteland",Estimate=regressionEstimate,
            OffenseIndex=regressionEstimate.Offense,DurabilityIndex=regressionEstimate.Durability,CompositeIndex=regressionEstimate.Score};
        var regressionPool=new List<Hero>{regressionFreja};
        regressionPool.AddRange(Enumerable.Range(0,4).Select(i=>new Hero{Name="Base "+i,AssetSlug="base-"+i,Role=i==0?"Melee":"Range",Estimate=new(10,10,10,10,10,"Recorded build"),OffenseIndex=10,DurabilityIndex=10,CompositeIndex=10}));
        var regressionSquads=(List<SquadResult>)optimize.Invoke(null,[regressionPool,PlannerMode.Balanced,true,1,"Unknown"])!;
        Check(regressionSquads.Count==1 && regressionSquads[0].Heroes.Any(h=>h.AssetSlug=="freja"),"Missing Shadow Guard excluded Freja from the optimiser");
        Check(!regressionBuild.Skills.ContainsKey("survivor_freja_skill_3"),"Scoring saved a default skill into the user's build");
        var farmingLucky=new Hero{Name="Lucky",AssetSlug="lucky",Role="Range",Estimate=new(1,1,1,1,1,"Recorded build",StaminaReductionPercent:16),OffenseIndex=1,DurabilityIndex=1,CompositeIndex=1};
        var farmingPool=regressionPool.Append(farmingLucky).ToList();
        var farmSquads=(List<SquadResult>)optimize.Invoke(null,[farmingPool,PlannerMode.Pve,true,1,"Unknown"])!;
        Check(farmSquads.Single().Heroes.Contains(farmingLucky) && farmSquads[0].StaminaReduction==16,"PvE farming did not prioritise known Stamina saving");
        farmingLucky.Estimate=farmingLucky.Estimate! with {StaminaReductionPercent=0};
        var combatFarmSquads=(List<SquadResult>)optimize.Invoke(null,[farmingPool,PlannerMode.Pve,true,1,"Unknown"])!;
        Check(!combatFarmSquads.Single().Heroes.Contains(farmingLucky),"Missing/locked economy still influenced farming ranking");
        Check(farmSquads[0].Score<combatFarmSquads[0].Score,"Stamina saving was falsely added to combat strength");
        var ranked = (List<SquadResult>)optimize.Invoke(null, [synthetic, PlannerMode.Balanced, false, 6, "Unknown"])!;
        Check(ranked[0].Heroes.Any(h => h.Faction == "Sea") && ranked[0].Heroes.Count(h => h.Faction == "Mountain") == 4,
            "Optimizer failed to prefer the Mariner's five-faction bonus over four-faction bonus");
        Check(Math.Abs(ranked[0].Score - 107) < 1e-9 && Math.Abs(ranked[0].FactionBonus - 7) < 1e-9,
            "Faction health is not included in the actual optimizer score");
        Check(ranked.All(r => Math.Abs(r.Score - r.BaseScore - r.SynergyBonus - r.FactionBonus - r.FrontlineBonus) < 1e-9), "Score breakdown disagrees with ranking");
        for (int i = 0; i < synthetic.Count; i++)
        {
            synthetic[i].Role = i == 0 ? "Melee" : i == 1 ? "Mid" : "Range";
            synthetic[i].DurabilityIndex = i == 0 ? 180 : i == 1 ? 20 : 100;
        }
        var positionRanked = (List<SquadResult>)optimize.Invoke(null, [synthetic, PlannerMode.Survival, false, 6, "Unknown"])!;
        Check(positionRanked.Any(r => Math.Abs(r.FrontlineBonus) > .01), "Position fit is missing from actual squad search");
        Check(positionRanked.All(r => Math.Abs(r.Score - r.BaseScore - r.SynergyBonus - r.FactionBonus - r.FrontlineBonus) < 1e-9), "Position score breakdown disagrees with ranking");
        var enemyPicker = (ComboBox)window.FindName("EnemyFactionPicker");
        enemyPicker.SelectedIndex = 3; // Sky target scenario.
        Check(((ComboBox)window.FindName("FormationEnemyFactionPicker")).SelectedIndex == 3, "Enemy faction selectors are not synchronized");
        Check(JsonSerializer.Deserialize<PlannerProfile>(File.ReadAllText(profilePath))!.EnemyFaction == "Sky", "Enemy scenario was not saved");
        enemyPicker.SelectedIndex = 0;
        Check(!((Expander)window.FindName("EstimateDetailsExpander")).IsExpanded, "Estimate details should be tucked away by default");
        Check(new HeroSkill { RaidLevelParameters = ["pve_effect|damage_heal_text|effect_param2|99"] }.DamageLabel.Contains("not simulated"), "Modifier falsely displayed as ATK damage");
        var legacySettings = new UpgradeSettings { Goal = "direct" }; legacySettings.Clean();
        Check(legacySettings.Goal == "power", "Legacy direct metric did not migrate safely");
        Check(becca.IsOwned && becca.Progress.Current is null, "Old profile lost ownership / invented stars");
        ((TabControl)window.FindName("InspectorTabs")).SelectedIndex = 3;
        Invoke(window, "HeroCard_Click", new Button { Tag = becca }, new RoutedEventArgs());
        Check(!becca.IsOwned, "Roster click did not unmark ownership");
        Invoke(window, "HeroCard_Click", new Button { Tag = becca }, new RoutedEventArgs());
        Check(becca.IsOwned, "Roster click did not mark ownership");
        ((TextBox)window.FindName("CurrentStars")).Text = "4";
        ((TextBox)window.FindName("TargetStars")).Text = "4";
        Invoke(window, "SaveStars_Click", new Button(), new RoutedEventArgs());
        Check(becca.Progress.Status == "reached", "Save stars failed");
        ((TextBox)window.FindName("CurrentStars")).Text = "-1";
        Invoke(window, "SaveStars_Click", new Button(), new RoutedEventArgs());
        Check(becca.Progress.Current == 4, "Invalid stars overwrote save");
        Check(JsonSerializer.Deserialize<PlannerProfile>(File.ReadAllText(profilePath))!.HeroProgress[becca.AssetSlug].Current == 4, "Stars not persisted");
        ((TabControl)window.FindName("InspectorTabs")).SelectedIndex = 0;
        foreach (var name in new[] { "Rosie", "Layla", "Becca", "Ray", "Maddie" })
        {
            heroes.Single(h => h.Name == name).IsOwned = true;
            Invoke(window, "HeroCard_Click", new Button { Tag = heroes.Single(h => h.Name == name) }, new RoutedEventArgs());
        }
        double referenceBecca = becca.CompositeIndex;
        var focus = (TextBox)window.FindName("FormationResourceFocus");
        Check(focus.Text.Contains("Record these builds"), "Unknown builds must not receive a guessed ranking");
        var data = Field<UpgradeData>(window, "_upgradeData");
        Check(((TextBlock)window.FindName("ConfigVersionText")).Text.Contains(data.ClientBuild), "Header build must match embedded progression data");
        Check(((TextBlock)window.FindName("RosterCountText")).Text.StartsWith(heroes.Count.ToString()), "Header roster count must match current heroes");
        Check(heroes.Select(h => h.AssetSlug).ToHashSet().SetEquals(data.Heroes.Keys), "Native roster/progression mismatch");
        foreach (var name in new[] { "Rosie", "Layla", "Becca", "Ray", "Maddie" })
        {
            var hero = heroes.Single(h => h.Name == name); bool ownedBefore = hero.IsOwned;
            Invoke(window, "EditBuild_Click", new Button { Tag = hero }, new RoutedEventArgs());
            Check(hero.IsOwned == ownedBefore, "Edit overlay changed ownership");
            Check(((Grid)window.FindName("BuildOverlay")).Visibility == Visibility.Visible, "Overlay not visible");
            Field<ComboBox>(window, "_rankEditor").SelectedIndex = 1;
            Field<ComboBox>(window, "_stageEditor").SelectedIndex = 1;
            Field<TextBox>(window, "_levelEditor").Text = "1";
            Field<ComboBox>(window, "_gearModeEditor").SelectedIndex = 1;
            var h = data.Heroes[hero.AssetSlug];
            foreach (var skill in h.Skills) Field<Dictionary<string, TextBox>>(window, "_skillEditors")[skill.Id].Text = h.Stages[0].SkillCaps[skill.Slot] > 0 ? "1" : "0";
            Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[hero.AssetSlug].Level == 1, "Native build not saved");
            Check(JsonSerializer.Deserialize<PlannerProfile>(File.ReadAllText(profilePath))!.HeroBuilds[hero.AssetSlug].Level == 1, "Edit did not save immediately to disk");
            Check(((Grid)window.FindName("BuildOverlay")).Visibility == Visibility.Visible, "Autosave unexpectedly closed overlay");
            Field<TextBox>(window, "_levelEditor").Text = "999";
            Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[hero.AssetSlug].Level == 1, "Invalid build overwrote save");
            Invoke(window, "CloseBuild_Click", new Button(), new RoutedEventArgs());
        }
        Check(focus.Text.Contains("per 100 resource units") && !focus.Text.Contains("Record these builds"), "Native upgrade ranking missing");
        var priorityPanel = (StackPanel)window.FindName("ResourcePriorityCards");
        Check(priorityPanel.Children.OfType<Expander>().Any(), "Resource cards missing");
        Check(Math.Abs(becca.CompositeIndex - referenceBecca) < 1e-8, "Equal comparator used saved low-star build");
        var basisPicker = (ComboBox)window.FindName("ComparisonBasisPicker");
        basisPicker.SelectedIndex = 2;
        Check(becca.CompositeIndex < referenceBecca && becca.Estimate!.Basis != "Reference build", "Explicit My builds mode did not use the recorded build");
        var partialHero=heroes.First(h=>h.Estimate?.MissingFields is {Length:>0});
        Check(partialHero.BuildDataLabel.StartsWith("Defaults")&&partialHero.IndexPrefix=="Base est. ","Missing-build defaults are not visible on the hero card");
        Check(heroes.All(h=>!h.ModelGapLabel.Contains("model gap")),"Score differences are mislabeled as model error");
        basisPicker.SelectedIndex = 1;
        Check(becca.CompositeIndex < referenceBecca && becca.Estimate!.Basis == "Max heroes, no gear" && becca.Estimate.ActiveSkillIds!.Length>0, "No-gear maximum mode did not model maximum hero skills");
        basisPicker.SelectedIndex = 0;
        Check(Math.Abs(becca.CompositeIndex - referenceBecca) < 1e-8, "Equal comparison did not restore fair reference score");
        var settings = Field<UpgradeSettings>(window, "_upgradeSettings");
        settings.Inventory["hero-xp"] = 100000;
        Invoke(window, "RefreshUpgradeViews");
        var beforeRecord = Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Copy();
        var rayHero = heroes.Single(h => h.AssetSlug == "ray");
        var unownedRequest = UpgradeModel.Evaluate(new[] { "ray" }, Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds"), data, settings).Candidates.First(c => c.Kind == "level" && c.Blocked is null);
        int rayLevel = Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")["ray"].Level!.Value;
        rayHero.IsOwned = false;
        Invoke(window, "RecordUpgrade_Click", new Button { Tag = unownedRequest }, new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")["ray"].Level == rayLevel, "Unowned hero received a recorded upgrade");
        rayHero.IsOwned = true; Invoke(window, "RefreshUpgradeViews");
        var candidate = UpgradeModel.Evaluate(new[] { "rosie", "layla", "becca", "ray", "maddie" },
            Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds"), data, settings).Candidates.First(c => c.Slug == becca.AssetSlug && c.Kind == "level" && c.Blocked is null);
        var recordButton = new Button { Tag = candidate };
        Invoke(window, "RecordUpgrade_Click", recordButton, new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Level == beforeRecord.Level + 1, "Record completed did not advance level");
        Check(settings.Inventory["hero-xp"] == 100000 - candidate.Cost["hero-xp"], "Recorded balance not deducted");
        Check(JsonSerializer.Deserialize<PlannerProfile>(File.ReadAllText(profilePath))!.HeroBuilds[becca.AssetSlug].Level == 2, "Recorded upgrade not saved to disk");
        Invoke(window, "RecordUpgrade_Click", recordButton, new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Level == 2, "Stale/double-click recorded twice");
        Invoke(window, "UndoUpgrade_Click", new Button(), new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Level == 1 && settings.Inventory["hero-xp"] == 100000, "Undo did not restore build and balance");
        var resourceFilter = (ComboBox)window.FindName("ResourceClassFilter");
        resourceFilter.SelectedIndex = 1;
        var fragmentGroups = priorityPanel.Children.OfType<Expander>().Where(e => e.Header.ToString()!.Contains("Hero fragments")).ToList();
        Check(fragmentGroups.Count == 1 && priorityPanel.Children.OfType<Expander>().Count() == 1, "Hero fragments must be compared in one shared group");
        var fragmentCards = (StackPanel)fragmentGroups.Single().Content;
        var fragmentTop = fragmentCards.Children.OfType<Border>().Select(b => ((StackPanel)b.Child).Children.OfType<WrapPanel>().Single().Children.OfType<Button>().First()).Select(b => (UpgradeCandidate)b.Tag).ToList();
        var expectedFragments = UpgradeModel.Evaluate(new[] { "rosie", "layla", "becca", "ray", "maddie" },
            Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds"), data, settings).Candidates.Where(c => c.Kind == "rank" && c.Blocked is null && c.Gain is not null)
            .OrderByDescending(c => c.Gain).ThenByDescending(c => c.Efficiency).ThenBy(c => c.Label, StringComparer.Ordinal).Take(3);
        Check(fragmentTop.Select(c => c.Label).SequenceEqual(expectedFragments.Select(c => c.Label)), "Shared fragment top three must rank across heroes by percent gain");
        resourceFilter.SelectedIndex = 3;
        Check(priorityPanel.Children.OfType<Expander>().First().Header.ToString()!.Contains("Hero XP"), "Resource class filter not applied");
        var xpCards = (StackPanel)priorityPanel.Children.OfType<Expander>().First().Content;
        Check(xpCards.Children.OfType<Border>().Count() <= 3, "More than top three choices displayed");
        var topCandidates = xpCards.Children.OfType<Border>().Select(b => ((StackPanel)b.Child).Children.OfType<WrapPanel>().Single().Children.OfType<Button>().First()).Select(b => (UpgradeCandidate)b.Tag).ToList();
        var expectedTop = UpgradeModel.Evaluate(new[] { "rosie", "layla", "becca", "ray", "maddie" },
            Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds"), data, settings).Candidates.Where(c => c.Group == "hero-xp" && c.Blocked is null && c.Gain is not null)
            .OrderByDescending(c => c.Efficiency).ThenByDescending(c => c.Gain).ThenBy(c => c.Label, StringComparer.Ordinal).Take(3).Select(c => c.Label);
        Check(topCandidates.Select(c => c.Label).SequenceEqual(expectedTop), "XP top three are not ordered by gain per XP");
        var gearChoices = new UpgradeResult { Candidates = [
            new("becca", "Costly gain", "gear", new() {{"gear-xp",1000}}, "gear-xp",8,.8,"unknown","",null,false,null),
            new("rosie", "Cheaper efficient gain", "gear", new() {{"gear-xp",100}}, "gear-xp",4,4,"unknown","",null,false,null)] };
        var gearPanel = new StackPanel();
        Invoke(window,"RenderUpgradeGroups",gearPanel,gearChoices,"all",true);
        var gearContent=(StackPanel)gearPanel.Children.OfType<Expander>().Single().Content;
        var bestGear=(UpgradeCandidate)((StackPanel)gearContent.Children.OfType<Border>().First().Child).Children.OfType<WrapPanel>().Single().Children.OfType<Button>().First().Tag;
        Check(bestGear.Label=="Cheaper efficient gain","Gear XP cards preferred larger raw gain over better XP value");
        Check(xpCards.Children.OfType<Border>().All(b => ((StackPanel)b.Child).Children.OfType<TextBox>().All(t => t.IsReadOnly)), "Priority card text is not selectable read-only text");
        settings.Inventory["hero-xp"] = 0;
        Invoke(window, "RecordUpgrade_Click", new Button { Tag = candidate }, new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Level == 1 && settings.Inventory["hero-xp"] == 0, "Insufficient recorded balance allowed an upgrade");
        settings.Inventory["hero-xp"] = 100000;
        var rankCandidate = UpgradeModel.Evaluate(new[] { "rosie", "layla", "becca", "ray", "maddie" },
            Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds"), data, settings).Candidates.First(c => c.Slug == becca.AssetSlug && c.Kind == "rank" && c.Blocked is null);
        Check(rankCandidate.Cost.Keys.All(id => !settings.Inventory.ContainsKey(id)), "Unknown fragment balance fixture is not unknown");
        Invoke(window, "RecordUpgrade_Click", new Button { Tag = rankCandidate }, new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Stage == rankCandidate.After!.Stage, "Rank record did not advance exact partial step");
        Check(rankCandidate.Cost.Keys.All(id => !settings.Inventory.ContainsKey(id)), "Unknown fragment balances were invented");
        var builds = Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds");
        builds[becca.AssetSlug].Level = 2;
        Invoke(window, "UndoUpgrade_Click", new Button(), new RoutedEventArgs());
        Check(builds[becca.AssetSlug].Level == 2, "Undo overwrote a later edit");
        builds[becca.AssetSlug].Level = 1;
        Invoke(window, "UndoUpgrade_Click", new Button(), new RoutedEventArgs());
        Check(builds[becca.AssetSlug].Stage == beforeRecord.Stage, "Rank undo did not restore original step");
        using (var lockedProfile = new FileStream(profilePath, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            Invoke(window, "RecordUpgrade_Click", new Button { Tag = candidate }, new RoutedEventArgs());
            Check(builds[becca.AssetSlug].Level == 1 && settings.Inventory["hero-xp"] == 100000, "Save failure changed build or inventory");
        }
        foreach (string kind in new[] { "skill", "gear" })
        {
            var advanced = beforeRecord.Copy(); advanced.Level = 120;
            advanced.Stage = data.Heroes[becca.AssetSlug].Stages.Single(s => s.Rank == 3 && s.Step == 6).Id;
            var gear = data.Gear.First(g => g.Value.HeroLevelRequired <= advanced.Level);
            advanced.Gear = [new() { Id = gear.Key, Level = gear.Value.Levels[0].Level }];
            builds[becca.AssetSlug] = advanced;
            var step = UpgradeModel.Evaluate(new[] { "rosie", "layla", "becca", "ray", "maddie" }, builds, data, settings).Candidates.First(c => c.Slug == becca.AssetSlug && c.Kind == kind && c.Blocked is null);
            Invoke(window, "RecordUpgrade_Click", new Button { Tag = step }, new RoutedEventArgs());
            Check(builds[becca.AssetSlug].Skills.OrderBy(x => x.Key).SequenceEqual(step.After!.Skills.OrderBy(x => x.Key)) &&
                builds[becca.AssetSlug].Gear!.Select(g => (g.Id, g.Level)).SequenceEqual(step.After.Gear!.Select(g => (g.Id, g.Level))), $"{kind} record wrong destination");
            Invoke(window, "UndoUpgrade_Click", new Button(), new RoutedEventArgs());
            Check(builds[becca.AssetSlug].Skills.OrderBy(x => x.Key).SequenceEqual(advanced.Skills.OrderBy(x => x.Key)) &&
                builds[becca.AssetSlug].Gear!.Select(g => (g.Id, g.Level)).SequenceEqual(advanced.Gear!.Select(g => (g.Id, g.Level))), $"{kind} undo wrong destination");
        }
        builds[becca.AssetSlug] = beforeRecord.Copy(); Invoke(window, "SaveProfile"); Invoke(window, "RefreshUpgradeViews");
        resourceFilter.SelectedIndex = 4;
        Check(priorityPanel.Children.OfType<Expander>().Count() == 0, "Empty gear filter retained other resources");
        resourceFilter.SelectedIndex = 0;
        ((ComboBox)window.FindName("FormationModePicker")).SelectedIndex = 2;
        Check(((ComboBox)window.FindName("ModePicker")).SelectedIndex == 2 && focus.Text.Contains("per 100 resource units"), "Formation mode picker not synchronized");
        Invoke(window, "EditBuild_Click", new Button { Tag = becca }, new RoutedEventArgs());
        Field<TextBox>(window, "_levelEditor").Text = "2";
        Field<ComboBox>(window, "_targetedPoolEditor").SelectedIndex = 1;
        Field<Expander>(window,"_buildComparison").IsExpanded=true; Invoke(window,"FlushBuildRefresh");
        var targetedText = (TextBox)window.FindName("TargetedResourceText");
        Check(targetedText.Text.Contains("TARGETED DRAFT") && targetedText.Text.Contains("Provisional target"), "Targeted recommendation missing");
        var draftCards = (StackPanel)window.FindName("TargetedDraftCards");
        Check(targetedText.Text.Length < 150 && draftCards.Children.OfType<Border>().Any(), "Targeted draft must use a concise recommendation and separate hero cards");
        Check(draftCards.Children.OfType<Border>().All(b => ((StackPanel)b.Child).Children.OfType<TextBox>().All(t => t.IsReadOnly)), "Draft card text must stay selectable");
        Check(draftCards.Children.OfType<Expander>().Any(e => e.Header.ToString()!.Contains("Pool rates") && !e.IsExpanded), "Pool/model notes must be collapsed by default");
        Check(Field<StackPanel>(window, "_overlayResults").Children.OfType<Expander>().Any(), "Overlay comparison must use structured resource groups");
        Check(Field<UpgradeSettings>(window, "_upgradeSettings").TargetedPool == "newbie_recuit_up_1", "Pool choice not autosaved");
        var refreshBefore=Field<int>(window,"_buildRefreshPasses");var burstTimer=System.Diagnostics.Stopwatch.StartNew();
        for(int burst=0;burst<20;burst++)Field<TextBox>(window,"_levelEditor").Text=(burst%2+1).ToString();
        burstTimer.Stop();Check(Field<int>(window,"_buildRefreshPasses")==refreshBefore,"Editing ran expensive refresh inline");
        Invoke(window,"FlushBuildRefresh");Check(Field<int>(window,"_buildRefreshPasses")==refreshBefore+1,"Burst edits did not coalesce to one refresh");
        Console.WriteLine($"Hero edit burst: 20 valid edits in {burstTimer.Elapsed.TotalMilliseconds:F1} ms; one queued refresh; profile writes remained immediate.");
        Field<Slider>(window, "_starSlider").Value = 5;
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Stage == data.Heroes[becca.AssetSlug].Stages[5].Id, "Star slider did not autosave exact partial rank");
        Check(Field<TextBlock>(window, "_starSliderLabel").Text.Contains("step 5/6"), "Partial-rank label missing");
        Check(Field<StackPanel>(window, "_starPreview").Children.Count == 5, "Star preview must have five slots");
        var partialImage = ((Grid)Field<StackPanel>(window, "_starPreview").Children[0]).Children.OfType<Image>().Last();
        var partialPath = (PathGeometry)partialImage.Clip;
        var partialPoints = ((PolyLineSegment)partialPath.Figures[0].Segments[0]).Points;
        Check(partialPoints[1].X < 18, "Partial star must fill counterclockwise from the top");
        void AssertStars(int rank, int step, string[] baseSprites, int? partialSlot = null, string? partialSprite = null)
        {
            var stage = data.Heroes[becca.AssetSlug].Stages.Single(s => s.Rank == rank && s.Step == step);
            var slots = StarProgress.Slots(stage);
            Check(slots.Select(s => s.BaseSprite).SequenceEqual(baseSprites), $"Wrong star row at {rank}/{step}");
            Check(slots.Where(s => s.ProgressSprite is not null).Count() == (partialSlot is null ? 0 : 1), "Wrong number of partial stars");
            if (partialSlot is int index) Check(slots[index].ProgressSprite == partialSprite && slots[index].Steps == step, "Wrong partial-star color/slot");
        }
        string empty = StarProgress.Empty, purple = StarProgress.Purple, gold = StarProgress.Gold;
        AssertStars(0, 0, [empty, empty, empty, empty, empty]);
        AssertStars(2, 1, [purple, empty, empty, empty, empty], 1, purple);
        AssertStars(3, 3, [purple, purple, empty, empty, empty], 2, purple);
        AssertStars(5, 6, [purple, purple, purple, purple, purple]);
        AssertStars(6, 1, [purple, purple, purple, purple, purple], 0, gold);
        AssertStars(8, 6, [gold, gold, gold, purple, purple]);
        AssertStars(10, 6, [gold, gold, gold, gold, gold]);
        Check(StarProgress.Label(null).Contains("unknown"), "Unknown stars are shown as zero");
        Check(StarProgress.Slots(new() { Rank = 11, Step = 1 }).Count == 0, "Unmodeled ascension display guessed");
        var captured = window.Content as FrameworkElement;
        captured!.Measure(new Size(1500, 920)); captured.Arrange(new Rect(0, 0, 1500, 920)); captured.UpdateLayout();
        void AssertRosterHeader(double width)
        {
            captured.Measure(new Size(width, 920)); captured.Arrange(new Rect(0, 0, width, 920)); captured.UpdateLayout();
            var title = (TextBlock)window.FindName("RosterTitle");
            var pickers = new[] { "ComparisonBasisPicker", "FactionFilter", "RoleFilter", "RarityFilter" }
                .Select(name => (ComboBox)window.FindName(name)).ToArray();
            var rowY = pickers[0].TranslatePoint(new Point(), captured).Y;
            Check(rowY >= title.TranslatePoint(new Point(), captured).Y + title.ActualHeight, "Roster filters overlap title");
            for (int i = 0; i < pickers.Length; i++)
            {
                var picker = pickers[i];
                Check(Math.Abs(picker.ActualHeight - 32) < 0.1, "Roster filter stretched vertically");
                Check(Math.Abs(picker.TranslatePoint(new Point(), captured).Y - rowY) < 0.1, "Roster filters are misaligned");
                Check(picker.ActualWidth >= 100, "Roster filter is too narrow for its label");
                if (i > 0)
                    Check(picker.TranslatePoint(new Point(), captured).X >= pickers[i - 1].TranslatePoint(new Point(), captured).X + pickers[i - 1].ActualWidth + 7,
                        "Roster filters overlap or lack spacing");
            }
        }
        AssertRosterHeader(1120);
        AssertRosterHeader(1500);
        IEnumerable<DependencyObject> Walk(DependencyObject parent)
        {
            for (int i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
            { var child = VisualTreeHelper.GetChild(parent, i); yield return child; foreach (var nested in Walk(child)) yield return nested; }
        }
        var roster = (ItemsControl)window.FindName("HeroRoster");
        int checkedBadges = 0, ascensionBadges = 0;
        foreach (var controls in Walk(roster).OfType<StackPanel>().Where(p => p.Name == "CardControls"))
        {
            var owned = controls.Children.OfType<CheckBox>().Single();
            var edit = controls.Children.OfType<Button>().Single();
            Check(edit.TranslatePoint(new Point(), controls).Y >= owned.TranslatePoint(new Point(), controls).Y + owned.ActualHeight,
                "Edit button overlaps ownership badge");
            var cardGrid = (Grid)controls.Parent;
            var asc = cardGrid.Children.OfType<Border>().Single(b => b.Name == "AscensionBadge");
            if (asc.Visibility == Visibility.Visible)
            {
                ascensionBadges++;
                Check(controls.TranslatePoint(new Point(), cardGrid).Y >= asc.TranslatePoint(new Point(), cardGrid).Y + asc.ActualHeight,
                    "Ownership controls overlap ASC badge");
            }
            if (owned.IsChecked == true)
            {
                checkedBadges++;
                Check(((TextBlock)owned.Template.FindName("OwnedMark", owned)).Visibility == Visibility.Visible,
                    "Owned green checkmark missing");
            }
        }
        Check(checkedBadges > 0 && ascensionBadges > 0, "Card layout assertions did not exercise owned/ASC badges");
        var image = new RenderTargetBitmap(1500, 920, 96, 96, PixelFormats.Pbgra32); image.Render(captured);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(image));
        var screenshot = Environment.GetEnvironmentVariable("PLANNER_NATIVE_SCREENSHOT");
        if (!string.IsNullOrWhiteSpace(screenshot)) { Directory.CreateDirectory(Path.GetDirectoryName(screenshot)!); using var output = File.Create(screenshot); encoder.Save(output); }
        Invoke(window, "CloseBuild_Click", new Button(), new RoutedEventArgs());
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Level == 2, "Closing lost an autosaved edit");
        var headerScreenshot = Environment.GetEnvironmentVariable("PLANNER_HEADER_SCREENSHOT");
        if (!string.IsNullOrWhiteSpace(headerScreenshot))
        {
            captured.UpdateLayout();
            var preview = new RenderTargetBitmap(1500, 920, 96, 96, PixelFormats.Pbgra32); preview.Render(captured);
            var previewEncoder = new PngBitmapEncoder(); previewEncoder.Frames.Add(BitmapFrame.Create(preview));
            Directory.CreateDirectory(Path.GetDirectoryName(headerScreenshot)!); using var output = File.Create(headerScreenshot); previewEncoder.Save(output);
        }
        var priorityScreenshot = Environment.GetEnvironmentVariable("PLANNER_PRIORITY_SCREENSHOT");
        var factionScreenshot = Environment.GetEnvironmentVariable("PLANNER_FACTION_SCREENSHOT");
        if (!string.IsNullOrWhiteSpace(factionScreenshot))
        {
            var guide = (ScrollViewer)window.FindName("FormationGuidePanel");
            guide.ScrollToTop(); captured.UpdateLayout();
            var preview = new RenderTargetBitmap(1500, 920, 96, 96, PixelFormats.Pbgra32); preview.Render(captured);
            var previewEncoder = new PngBitmapEncoder(); previewEncoder.Frames.Add(BitmapFrame.Create(preview));
            Directory.CreateDirectory(Path.GetDirectoryName(factionScreenshot)!); using var output = File.Create(factionScreenshot); previewEncoder.Save(output);
        }
        if (!string.IsNullOrWhiteSpace(priorityScreenshot))
        {
            resourceFilter.SelectedIndex = 3;
            var guide = (ScrollViewer)window.FindName("FormationGuidePanel");
            var priorityText = (TextBox)window.FindName("FormationResourceFocus");
            captured.UpdateLayout();
            var point = priorityText.TranslatePoint(new Point(), guide);
            guide.ScrollToVerticalOffset(guide.VerticalOffset + point.Y - 25); captured.UpdateLayout();
            var preview = new RenderTargetBitmap(1500, 920, 96, 96, PixelFormats.Pbgra32); preview.Render(captured);
            var previewEncoder = new PngBitmapEncoder(); previewEncoder.Frames.Add(BitmapFrame.Create(preview));
            Directory.CreateDirectory(Path.GetDirectoryName(priorityScreenshot)!); using var output = File.Create(priorityScreenshot); previewEncoder.Save(output);
        }
        var targetedScreenshot = Environment.GetEnvironmentVariable("PLANNER_TARGETED_SCREENSHOT");
        if (!string.IsNullOrWhiteSpace(targetedScreenshot))
        {
            var guide = (ScrollViewer)window.FindName("FormationGuidePanel");
            captured.UpdateLayout();
            var point = targetedText.TranslatePoint(new Point(), guide);
            guide.ScrollToVerticalOffset(guide.VerticalOffset + point.Y - 25); captured.UpdateLayout();
            var preview = new RenderTargetBitmap(1500, 920, 96, 96, PixelFormats.Pbgra32); preview.Render(captured);
            var previewEncoder = new PngBitmapEncoder(); previewEncoder.Frames.Add(BitmapFrame.Create(preview));
            Directory.CreateDirectory(Path.GetDirectoryName(targetedScreenshot)!); using var output = File.Create(targetedScreenshot); previewEncoder.Save(output);
        }
        window.Left=-5000;window.Top=-5000;window.ShowActivated=false;window.Show();
        window.UpdateLayout();
        var ownedControl=Walk(window).OfType<CheckBox>().First(c=>c.Name=="OwnedCheck");
        bool captureOwnedBefore=ownedControl.IsChecked==true;
        var selectedBefore=Field<System.Collections.ObjectModel.ObservableCollection<Hero>>(window,"_selected").Select(h=>h.AssetSlug).ToArray();
        void ReleaseCheckboxThroughRoutedEvents()
        {
            Check(ownedControl.CaptureMouse(),"Could not establish checkbox click capture");
            var setPressed=typeof(System.Windows.Controls.Primitives.ButtonBase).GetMethod("SetIsPressed",BindingFlags.Instance|BindingFlags.NonPublic)!;
            setPressed.Invoke(ownedControl,[true]);
            var up=new System.Windows.Input.MouseButtonEventArgs(System.Windows.Input.Mouse.PrimaryDevice,Environment.TickCount,System.Windows.Input.MouseButton.Left){RoutedEvent=UIElement.PreviewMouseLeftButtonUpEvent};
            ownedControl.RaiseEvent(up);
            if(!up.Handled){up.RoutedEvent=UIElement.MouseLeftButtonUpEvent;ownedControl.RaiseEvent(up);}
            Check(!ReferenceEquals(System.Windows.Input.Mouse.Captured,ownedControl),"Ownership checkbox trapped mouse capture after release");
        }
        ReleaseCheckboxThroughRoutedEvents();
        Check((ownedControl.IsChecked==true)!=captureOwnedBefore,"Normal ownership click failed to toggle exactly once");
        Check(selectedBefore.SequenceEqual(Field<System.Collections.ObjectModel.ObservableCollection<Hero>>(window,"_selected").Select(h=>h.AssetSlug)),"Ownership checkbox also changed squad selection");
        ReleaseCheckboxThroughRoutedEvents();
        Check((ownedControl.IsChecked==true)==captureOwnedBefore,"Second ownership click failed to restore state without Tab");
        Exception? contextError=null;
        window.Dispatcher.BeginInvoke(new Action(()=>{
            var modal=Application.Current.Windows.OfType<Window>().Single(w=>w!=window&&w.Title=="Signature Gear, Behemoth & Research");
            try{
                modal.UpdateLayout();
                var elements=Walk(modal).ToList();
                elements.OfType<CheckBox>().Single(x=>x.Content?.ToString()=="Apply recorded stat context").IsChecked=true;
                var stats=elements.OfType<TextBox>().Where(x=>x.Width==150).ToArray();Check(stats.Length==3,"Behemoth bonus fields missing");stats[0].Text="348";stats[1].Text="70";stats[2].Text="23184";
                foreach(var expander in elements.OfType<Expander>())expander.IsExpanded=true;
                modal.UpdateLayout();elements=Walk(modal).ToList();
                var source=elements.OfType<ComboBox>().Single(x=>x.Items.OfType<ComboBoxItem>().Any(i=>i.Tag?.ToString()=="configured"));source.SelectedIndex=1;
                foreach(string kind in new[]{"behemoth-level","behemoth-star"})elements.OfType<ComboBox>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)==kind+" caser").SelectedIndex=1;
                var signature=elements.OfType<ComboBox>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)=="signature rosie");signature.SelectedIndex=1;
                var research=elements.OfType<ComboBox>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)=="research new_hero_all_hero_attack");research.SelectedIndex=2;
                elements.OfType<Button>().Single(x=>x.Content?.ToString()=="Apply").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            }catch(Exception ex){contextError=ex;modal.Close();}
        }),System.Windows.Threading.DispatcherPriority.Loaded);
        Invoke(window,"ArmyContext_Click",new Button(),new RoutedEventArgs());
        if(contextError is not null)throw contextError;
        var contextSaved=JsonSerializer.Deserialize<PlannerProfile>(File.ReadAllText(profilePath))!.ArmyContext;
        Check(contextSaved.Enabled&&contextSaved.Signature["rosie"]==1&&contextSaved.Research["new_hero_all_hero_attack"]==2&&contextSaved.Behemoth[0]==348&&contextSaved.BehemothSource=="configured"&&contextSaved.BehemothBuilds["caser"].Level==1&&contextSaved.BehemothBuilds["caser"].Star==1,"Army stat context did not save through the native dialog");
        Check(Walk((StackPanel)window.FindName("StatsSignaturePanel")).OfType<CheckBox>().All(x=>x.IsChecked==true),"Hero Signature UI was stale after context dialog Apply");
        Invoke(window,"SetActiveHero",heroes.Single(h=>h.AssetSlug=="rosie"));
        Invoke(window,"Navigation_Click",(Button)window.FindName("StatsNav"),new RoutedEventArgs());window.UpdateLayout();
        var themedCombo=(ComboBox)window.FindName("FactionFilter");themedCombo.ApplyTemplate();
        var themedToggle=Walk(themedCombo).OfType<System.Windows.Controls.Primitives.ToggleButton>().First();
        typeof(System.Windows.Controls.Primitives.ToggleButton).GetMethod("OnClick",BindingFlags.Instance|BindingFlags.NonPublic)!.Invoke(themedToggle,null);
        window.UpdateLayout();Check(themedCombo.IsDropDownOpen,"Styled ComboBox did not open on toggle click");
        var themedPopup=(System.Windows.Controls.Primitives.Popup)themedCombo.Template.FindName("PART_Popup",themedCombo);
        Check(themedPopup.IsOpen&&themedPopup.Child is Border,"Styled ComboBox popup missing");
        themedCombo.SelectedIndex=1;Check(((ComboBoxItem)themedCombo.SelectedItem).Content?.ToString()=="Mountain","Styled dropdown selection failed");
        themedCombo.IsDropDownOpen=false;themedCombo.SelectedIndex=0;
        var signatureView=(StackPanel)window.FindName("StatsSignaturePanel");
        var localSignature=Walk(signatureView).OfType<ComboBox>().Single();localSignature.SelectedIndex=2;
        Walk(signatureView).OfType<Button>().Single(x=>x.Content?.ToString()=="Save Signature Gear").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(Field<ArmyContextSettings>(window,"_armyContext").Signature["rosie"]==2,"Hero-local Signature save failed");
        Invoke(window,"Navigation_Click",(Button)window.FindName("BehemothsNav"),new RoutedEventArgs());window.UpdateLayout();
        var beastView=(StackPanel)window.FindName("BehemothsPanel");
        Check(Walk(beastView).OfType<Image>().Count(x=>x.Width==76)==2,"Behemoth icons missing");
        var beastLevel=Walk(beastView).OfType<TextBox>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)=="Behemoth caser level");
        beastLevel.Text="2";window.UpdateLayout();var levelCaret=beastLevel.GetRectFromCharacterIndex(0);Check(levelCaret.Top>=0&&levelCaret.Bottom<=beastLevel.ActualHeight-1,"Styled level input clips its text");
        foreach(int n in new[]{1,6,30,31,360,900}){var slots=BehemothStarProgress.Slots(n);Check(slots.Count==5&&slots.All(x=>x.Steps>=0&&x.Steps<=6&&x.Overlay<=12),"Behemoth star display out of bounds");}
        var themedStarSlider=Walk(beastView).OfType<Slider>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)=="Behemoth caser star");themedStarSlider.ApplyTemplate();
        var themedTrack=(System.Windows.Controls.Primitives.Track)themedStarSlider.Template.FindName("PART_Track",themedStarSlider);double dragBefore=themedStarSlider.Value;
        themedTrack.Thumb.RaiseEvent(new System.Windows.Controls.Primitives.DragStartedEventArgs(0,0){RoutedEvent=System.Windows.Controls.Primitives.Thumb.DragStartedEvent});
        themedTrack.Thumb.RaiseEvent(new System.Windows.Controls.Primitives.DragDeltaEventArgs(30,0){RoutedEvent=System.Windows.Controls.Primitives.Thumb.DragDeltaEvent});
        Check(themedStarSlider.Value>dragBefore,"Styled star slider did not respond to thumb drag");
        themedTrack.Thumb.RaiseEvent(new System.Windows.Controls.Primitives.DragCompletedEventArgs(30,0,false){RoutedEvent=System.Windows.Controls.Primitives.Thumb.DragCompletedEvent});
        Walk(beastView).OfType<Slider>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)=="Behemoth caser star").Value=2;
        Walk(beastView).OfType<Button>().Single(x=>x.Content?.ToString()=="Save Behemoths").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        var screenshotDir=Environment.GetEnvironmentVariable("PLANNER_SCREENSHOT_DIR");
        if(!string.IsNullOrEmpty(screenshotDir)){
            void Capture(string name){window.UpdateLayout();var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(screenshotDir,name));encoder.Save(stream);}
            Capture("native-behemoths.png");
            Invoke(window,"Navigation_Click",(Button)window.FindName("StatsNav"),new RoutedEventArgs());Capture("native-signature.png");
        }
        var afterBeast=Field<ArmyContextSettings>(window,"_armyContext");
        Check(afterBeast.Signature["rosie"]==2&&afterBeast.Research["new_hero_all_hero_attack"]==2&&afterBeast.BehemothBuilds["caser"].Star==2,"Behemoth tab overwrote other context sources");
        Invoke(window,"Navigation_Click",(Button)window.FindName("ResearchNav"),new RoutedEventArgs());window.UpdateLayout();
        var researchHeader=(StackPanel)window.FindName("ResearchPanel");
        var treePicker=Walk(researchHeader).OfType<ComboBox>().Single();treePicker.SelectedItem=treePicker.Items.OfType<ComboBoxItem>().Single(i=>i.Tag?.ToString()=="4300006");window.UpdateLayout();
        ComboBox ResearchPicker()=>Walk((StackPanel)window.FindName("ResearchCardsPanel")).OfType<ComboBox>().Single(x=>System.Windows.Automation.AutomationProperties.GetName(x)=="Research node new_hero_all_hero_attack");
        ResearchPicker().SelectedIndex=3;
        Check(Field<ArmyContextSettings>(window,"_armyContext").Research["new_hero_all_hero_attack"]==2,"Research draft saved prematurely");
        Invoke(window,"Navigation_Click",(Button)window.FindName("BehemothsNav"),new RoutedEventArgs());
        Invoke(window,"Navigation_Click",(Button)window.FindName("ResearchNav"),new RoutedEventArgs());window.UpdateLayout();
        Check(ResearchPicker().SelectedIndex==3,"Research draft lost on tab switch");
        Walk((StackPanel)window.FindName("ResearchPanel")).OfType<Button>().Single(x=>x.Content?.ToString()=="Discard edits").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        window.UpdateLayout();Check(ResearchPicker().SelectedIndex==2,"Research discard changed saved level");
        ResearchPicker().SelectedIndex=3;
        Walk((StackPanel)window.FindName("ResearchPanel")).OfType<Button>().Single(x=>x.Content?.ToString()=="Save Research").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(Field<ArmyContextSettings>(window,"_armyContext").Research["new_hero_all_hero_attack"]==3,"Research save failed");
        Check(Field<ArmyContextSettings>(window,"_armyContext").Signature["rosie"]==2&&Field<ArmyContextSettings>(window,"_armyContext").BehemothBuilds["caser"].Star==2,"Research save overwrote other sources");
        if(!string.IsNullOrEmpty(screenshotDir)){window.UpdateLayout();var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);var researchEncoder=new PngBitmapEncoder();researchEncoder.Frames.Add(BitmapFrame.Create(bitmap));using var researchStream=File.Create(Path.Combine(screenshotDir,"native-research.png"));researchEncoder.Save(researchStream);}
        Exception? setupError=null;
        window.Dispatcher.BeginInvoke(new Action(()=>{
            var setup=Application.Current.Windows.OfType<Window>().Single(w=>w!=window&&w.Title=="Army Setup");
            try{setup.UpdateLayout();var elements=Walk(setup).ToList();elements.OfType<ComboBox>().Single().SelectedIndex=1;elements.OfType<Button>().Single(x=>x.Content?.ToString()=="Configure Research").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));}
            catch(Exception ex){setupError=ex;setup.Close();}
        }),System.Windows.Threading.DispatcherPriority.Loaded);
        Invoke(window,"ArmySetup_Click",new Button(),new RoutedEventArgs());if(setupError is not null)throw setupError;
        Check(Field<ArmyContextSettings>(window,"_armyContext").Scene=="pve"&&((TabControl)window.FindName("InspectorTabs")).SelectedIndex==6,"Army Setup failed to save settings and open Research");
        ((TabControl)window.FindName("InspectorTabs")).SelectedIndex=0;
        Invoke(window,"Clear_Click",new Button(),new RoutedEventArgs());
        Invoke(window,"HeroCard_Click",new Button{Tag=heroes.Single(h=>h.AssetSlug=="rosie")},new RoutedEventArgs());
        Field<ComboBox>(window,"ModePicker").SelectedIndex=2;
        Invoke(window,"Army_Click",new Button{Tag="1"},new RoutedEventArgs());
        Check(Field<IList<Hero>>(window,"_selected").Count==0,"Army 2 should start empty");
        Invoke(window,"HeroCard_Click",new Button{Tag=heroes.Single(h=>h.AssetSlug=="rosie")},new RoutedEventArgs());
        Check(Field<IList<Hero>>(window,"_selected").Count==0,"Reserved hero entered a second army");
        Invoke(window,"HeroCard_Click",new Button{Tag=becca},new RoutedEventArgs());
        Field<ComboBox>(window,"ModePicker").SelectedIndex=1;
        Invoke(window,"Army_Click",new Button{Tag="0"},new RoutedEventArgs());
        Check(Field<IList<Hero>>(window,"_selected").Single().AssetSlug=="rosie"&&Field<ComboBox>(window,"ModePicker").SelectedIndex==2,"Army 1 or its mode was lost");
        Invoke(window,"Clear_Click",new Button(),new RoutedEventArgs());
        Invoke(window,"Army_Click",new Button{Tag="4"},new RoutedEventArgs());
        Field<ComboBox>(window,"ComparisonBasisPicker").SelectedItem=Field<ComboBox>(window,"ComparisonBasisPicker").Items.Cast<ComboBoxItem>().Single(i=>(string)i.Tag=="reference");
        Field<ComboBox>(window,"AccessPicker").SelectedIndex=0;
        Invoke(window,"Optimize_Click",new Button(),new RoutedEventArgs());
        Check(Field<IList<Hero>>(window,"_selected").Count==5&&!Field<IList<Hero>>(window,"_selected").Any(h=>h.AssetSlug=="becca"),"Army 5 optimizer used an already allocated hero");
        Check(((StackPanel)window.FindName("SquadDataNotice")).Children.OfType<Expander>().Any(),"Incomplete squad did not request build data");
        foreach(var name in new[]{"ReleaseNav","ResearchNav","BehemothsNav","ArmyContextButton"})Check(((Button)window.FindName(name)).Margin.Right==6,"Navigation spacing differs: "+name);
        Invoke(window,"Clear_Click",new Button(),new RoutedEventArgs());
        Invoke(window,"Army_Click",new Button{Tag="1"},new RoutedEventArgs());
        Check(Field<IList<Hero>>(window,"_selected").Single().AssetSlug=="becca"&&Field<ComboBox>(window,"ModePicker").SelectedIndex==1,"Army 2 was overwritten");
        var armySave=JsonSerializer.Deserialize<PlannerProfile>(File.ReadAllText(profilePath))!;
        Check(armySave.Armies.Count==5&&armySave.ActiveArmy==1&&armySave.Armies.SelectMany(a=>a.Heroes).Distinct().Count()==armySave.Armies.Sum(a=>a.Heroes.Count),"Army assignments did not persist uniquely");
        var dirtyArmies=ArmyRoster.Clean([new(){Heroes=["a","a","bad","b","c","d","e","f"]},new(){Heroes=["b","f","g"]}],new[]{"a","b","c","d","e","f","g"});
        Check(dirtyArmies[0].Heroes.SequenceEqual(new[]{"a","b","c","d","e"})&&dirtyArmies[1].Heroes.SequenceEqual(new[]{"f","g"}),"Malformed army migration failed");
        if(!string.IsNullOrEmpty(screenshotDir)){window.UpdateLayout();var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);var armyEncoder=new PngBitmapEncoder();armyEncoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(screenshotDir,"native-five-armies.png"));armyEncoder.Save(stream);}
        Field<ComboBox>(window,"ComparisonBasisPicker").SelectedItem=Field<ComboBox>(window,"ComparisonBasisPicker").Items.Cast<ComboBoxItem>().Single(i=>(string)i.Tag=="recorded");
        foreach(var h in heroes.Where(h=>Field<Dictionary<string,HeroBuild>>(window,"_heroBuilds").ContainsKey(h.AssetSlug)&&h.AssetSlug!="becca"))Invoke(window,"HeroCard_Click",new Button{Tag=h},new RoutedEventArgs());
        var noExposure=((TextBlock)window.FindName("FormationScoreLabel")).Text;
        ((CheckBox)window.FindName("SurvivalToggle")).IsChecked=true;
        Check(((TextBlock)window.FindName("SurvivalNotice")).Text.Contains("Reference survival:"),"Predicted survival times missing");
        Check(((TextBlock)window.FindName("FormationScoreLabel")).Text.Contains("exposure benchmark")&&((TextBlock)window.FindName("FormationScoreLabel")).Text!=noExposure,"Survival projection did not change actual squad score");
        ((CheckBox)window.FindName("SurvivalToggle")).IsChecked=false;Check(((TextBlock)window.FindName("FormationScoreLabel")).Text==noExposure,"Disabling survival changed original scoring");
        ((CheckBox)window.FindName("SurvivalToggle")).IsChecked=true;
        if(!string.IsNullOrEmpty(screenshotDir)){window.UpdateLayout();var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);var survivalEncoder=new PngBitmapEncoder();survivalEncoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(screenshotDir,"survival-benchmark-native.png"));survivalEncoder.Save(stream);}
        foreach(var h in heroes.Where(h=>Field<Dictionary<string,HeroBuild>>(window,"_heroBuilds").ContainsKey(h.AssetSlug)&&h.AssetSlug!="becca"))Invoke(window,"HeroCard_Click",new Button{Tag=h},new RoutedEventArgs());
        window.Close();
        var reopened = Create();
        Check(Field<string>(reopened,"_comparisonBasis")=="recorded","Build comparison dropdown reset after reopen");
        Check(Field<bool>(reopened,"_survivalBenchmark")&&((CheckBox)reopened.FindName("SurvivalToggle")).IsChecked==true,"Survival option did not persist");
        Check(Field<ArmyContextSettings>(reopened,"_armyContext").Enabled&&Field<ArmyContextSettings>(reopened,"_armyContext").BehemothBuilds["caser"].Star==2,"Army context missing after reopen");

        Invoke(reopened, "SetActiveHero", ((List<Hero>)typeof(MainWindow).GetField("_heroes", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(reopened)!).Single(h => h.Name == "Becca"));
        Check(((TextBox)reopened.FindName("CurrentStars")).Text == "4", "Stars missing after reopen");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds").Count == 5, "Native builds missing after reopen");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds")[becca.AssetSlug].Gear!.Count == 0, "Explicit no-gear state lost");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds")[becca.AssetSlug].Level == 2, "Autosaved edit missing after reopen");
        Check(Field<UpgradeSettings>(reopened, "_upgradeSettings").TargetedPool == "newbie_recuit_up_1", "Targeted pool missing after reopen");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds")[becca.AssetSlug].Stage == data.Heroes[becca.AssetSlug].Stages[5].Id, "Partial rank missing after reopen");
        Check(Field<int>(reopened,"_activeArmy")==1&&Field<IList<Hero>>(reopened,"_selected").Single().AssetSlug=="becca","Army state missing after reopen");
        reopened.Close();
        var reviewWindow=Create();reviewWindow.Show();reviewWindow.UpdateLayout();var freja=Field<List<Hero>>(reviewWindow,"_heroes").Single(h=>h.AssetSlug=="freja");
        var reviewBuilds=Field<Dictionary<string,HeroBuild>>(reviewWindow,"_heroBuilds");var fd=data.Heroes["freja"];var fs=fd.Stages.Last();
        reviewBuilds["freja"]=new(){Stage=fs.Id,Level=fs.LevelMax,Skills=fd.Skills.ToDictionary(k=>k.Id,k=>0),Gear=[]};
        reviewBuilds["freja"].Skills.Remove(fd.Skills.Last().Id);
        var selection=Field<System.Collections.ObjectModel.ObservableCollection<Hero>>(reviewWindow,"_selected");selection.Clear();selection.Add(freja);
        Invoke(reviewWindow,"RefreshSquadDataNotice");
        Check(Walk((StackPanel)reviewWindow.FindName("SquadDataNotice")).OfType<Expander>().Single().Header.ToString()!.Contains("incomplete"),"Missing build notice absent");
        Invoke(reviewWindow,"EditBuild_Click",new Button{Tag=freja},new RoutedEventArgs());
        Field<Dictionary<string,TextBox>>(reviewWindow,"_skillEditors")[fd.Skills.Last().Id].Text="0";
        Check(!Walk((StackPanel)reviewWindow.FindName("SquadDataNotice")).OfType<Expander>().Single().Header.ToString()!.Contains("incomplete"),"Completeness notice stayed stale after a saved edit in max comparison mode");
        var editorRoot=(StackPanel)reviewWindow.FindName("BuildFields");
        foreach(var expander in Walk(editorRoot).OfType<Expander>().ToList())expander.IsExpanded=true;reviewWindow.UpdateLayout();
        Check(Walk(editorRoot).OfType<Button>().Count(b=>System.Windows.Automation.AutomationProperties.GetName(b).StartsWith("Gear slot "))==21,"Selectable gear panels missing");
        Walk(editorRoot).OfType<Button>().Single(b=>b.Content?.ToString()=="I checked this build in game").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(reviewBuilds["freja"].ReviewedUtc is not null,"Explicit review did not record date");
        Check(!Walk((StackPanel)reviewWindow.FindName("SquadDataNotice")).OfType<Button>().Any(b=>ReferenceEquals(b.Tag,freja)),"Review notice failed to clear");
        data.SourceHashes["review_test"]="changed";Invoke(reviewWindow,"RefreshSquadDataNotice");
        // The window has its own parsed catalog; mutate that instance to emulate a same-build hotfix.
        var reviewedData=Field<UpgradeData>(reviewWindow,"_upgradeData");reviewedData.SourceHashes["review_test"]="changed";Invoke(reviewWindow,"RefreshSquadDataNotice");
        Check(Walk((StackPanel)reviewWindow.FindName("SquadDataNotice")).OfType<Expander>().Single().Header.ToString()!.Contains("Review squad data"),"Same-build data change did not request revalidation");reviewedData.SourceHashes.Remove("review_test");data.SourceHashes.Remove("review_test");
        reviewBuilds["freja"].ReviewedUtc=DateTimeOffset.UtcNow.AddDays(-15);Invoke(reviewWindow,"RefreshSquadDataNotice");
        Check(Walk((StackPanel)reviewWindow.FindName("SquadDataNotice")).OfType<Expander>().Single().Header.ToString()!.Contains("Review squad data"),"Expired review not detected");
        Field<TextBox>(reviewWindow,"_levelEditor").Text=(fs.LevelMax-1).ToString();
        Check(reviewBuilds["freja"].ReviewedUtc<DateTimeOffset.UtcNow.AddDays(-14),"Single edit falsely reviewed untouched build data");
        foreach(double raw in new[]{-10d,0d,1d,100d,500d,10000d})Check(ScoreDisplay.Value(raw)==raw,"Formatting changed the actual model scale");
        Check(ScoreDisplay.Value(120)>ScoreDisplay.Value(110),"Display scale flattened normal model differences");
        var parityBasisPicker=(ComboBox)reviewWindow.FindName("ComparisonBasisPicker");
        var equalModels=Field<EstimateData>(reviewWindow,"_estimates");
        var parityHeroes=Field<List<Hero>>(reviewWindow,"_heroes").Where(h=>new[]{"rosie","freja","becca","maddie","ray"}.Contains(h.AssetSlug)).ToList();
        selection.Clear();foreach(var h in parityHeroes){selection.Add(h);reviewBuilds[h.AssetSlug]=EstimateModel.MaximumBuild(h.AssetSlug,equalModels,true);}
        Field<ArmyContextSettings>(reviewWindow,"_armyContext").Enabled=false;
        parityBasisPicker.SelectedItem=parityBasisPicker.Items.Cast<ComboBoxItem>().Single(i=>i.Tag?.ToString()=="reference");
        Invoke(reviewWindow,"RefreshEstimates");((CheckBox)reviewWindow.FindName("SurvivalToggle")).IsChecked=true;Invoke(reviewWindow,"UpdateSquadPresentation");
        Check(((CheckBox)reviewWindow.FindName("SurvivalToggle")).IsEnabled,"Equal builds incorrectly disabled the shared survival model");
        var equalFormation=((TextBlock)reviewWindow.FindName("FormationScoreLabel")).Text;var equalNotice=((TextBlock)reviewWindow.FindName("SurvivalNotice")).Text;
        var sameScores=parityHeroes.ToDictionary(h=>h.AssetSlug,h=>h.CompositeIndex);
        parityBasisPicker.SelectedItem=parityBasisPicker.Items.Cast<ComboBoxItem>().Single(i=>i.Tag?.ToString()=="recorded");
        Check(parityHeroes.All(h=>h.CompositeIndex==sameScores[h.AssetSlug]),"Combat scores depend on the build-mode label");
        Check(((TextBlock)reviewWindow.FindName("FormationScoreLabel")).Text==equalFormation&&((TextBlock)reviewWindow.FindName("SurvivalNotice")).Text==equalNotice,"Identical builds changed forecast or formation scoring between modes");
        Invoke(reviewWindow,"CloseBuild_Click",new Button(),new RoutedEventArgs());reviewWindow.UpdateLayout();
        foreach(var card in Walk((ItemsControl)reviewWindow.FindName("HeroRoster")).OfType<Button>().Where(b=>b.Tag is Hero&&b.Content is Border)){
            var grid=(Grid)((Border)card.Content).Child;var footer=grid.Children.OfType<Border>().Single(b=>Grid.GetRow(b)==1);
            var last=((StackPanel)footer.Child).Children.OfType<TextBlock>().Last();
            Check(last.TranslatePoint(new Point(),footer).Y+last.ActualHeight+footer.Padding.Bottom<=footer.ActualHeight+1,"Hero card clips its build-data status");
        }
        var defaultScreenshot=Environment.GetEnvironmentVariable("PLANNER_DEFAULTS_SCREENSHOT");
        if(!string.IsNullOrWhiteSpace(defaultScreenshot)){
            reviewWindow.UpdateLayout();var preview=new RenderTargetBitmap((int)reviewWindow.ActualWidth,(int)reviewWindow.ActualHeight,96,96,PixelFormats.Pbgra32);preview.Render(reviewWindow);
            var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(preview));using var stream=File.Create(defaultScreenshot);png.Save(stream);
        }
        reviewWindow.Close();
        app.Shutdown();
        Console.WriteLine("WPF UI regression passed: ownership, autosave, star layout, selectable priority cards, resource filters, top-three percent ordering, rank/level/skill/gear recording, balance deduction, stale-click protection, save rollback and safe Undo. Real profile untouched.");
    }
}
