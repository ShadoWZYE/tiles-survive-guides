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
        var app = new App();
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
        Check(heroes.Where(h => h.Rarity == "SSR").Select(h => Math.Round(h.CompositeIndex, 3)).Distinct().Count() > 5, "SSR reference estimates collapsed into ties");
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
        basisPicker.SelectedIndex = 1;
        Check(becca.CompositeIndex == 100 && becca.Estimate!.Basis == "Flat max stats", "Flat stats mode not restored from original config indices");
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
            .OrderByDescending(c => c.Gain).ThenByDescending(c => c.Efficiency).ThenBy(c => c.Label, StringComparer.Ordinal).Take(3).Select(c => c.Label);
        Check(topCandidates.Select(c => c.Label).SequenceEqual(expectedTop), "Top three are not ordered by percentage increase");
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
        var targetedText = (TextBox)window.FindName("TargetedResourceText");
        Check(targetedText.Text.Contains("TARGETED DRAFT") && targetedText.Text.Contains("Provisional target"), "Targeted recommendation missing");
        var draftCards = (StackPanel)window.FindName("TargetedDraftCards");
        Check(targetedText.Text.Length < 150 && draftCards.Children.OfType<Border>().Any(), "Targeted draft must use a concise recommendation and separate hero cards");
        Check(draftCards.Children.OfType<Border>().All(b => ((StackPanel)b.Child).Children.OfType<TextBox>().All(t => t.IsReadOnly)), "Draft card text must stay selectable");
        Check(draftCards.Children.OfType<Expander>().Any(e => e.Header.ToString()!.Contains("Pool rates") && !e.IsExpanded), "Pool/model notes must be collapsed by default");
        Check(Field<StackPanel>(window, "_overlayResults").Children.OfType<Expander>().Any(), "Overlay comparison must use structured resource groups");
        Check(Field<UpgradeSettings>(window, "_upgradeSettings").TargetedPool == "newbie_recuit_up_1", "Pool choice not autosaved");
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
        window.Close();
        var reopened = Create();
        Invoke(reopened, "SetActiveHero", ((List<Hero>)typeof(MainWindow).GetField("_heroes", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(reopened)!).Single(h => h.Name == "Becca"));
        Check(((TextBox)reopened.FindName("CurrentStars")).Text == "4", "Stars missing after reopen");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds").Count == 5, "Native builds missing after reopen");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds")[becca.AssetSlug].Gear!.Count == 0, "Explicit no-gear state lost");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds")[becca.AssetSlug].Level == 2, "Autosaved edit missing after reopen");
        Check(Field<UpgradeSettings>(reopened, "_upgradeSettings").TargetedPool == "newbie_recuit_up_1", "Targeted pool missing after reopen");
        Check(Field<Dictionary<string, HeroBuild>>(reopened, "_heroBuilds")[becca.AssetSlug].Stage == data.Heroes[becca.AssetSlug].Stages[5].Id, "Partial rank missing after reopen");
        reopened.Close();
        app.Shutdown();
        Console.WriteLine("WPF UI regression passed: ownership, autosave, star layout, selectable priority cards, resource filters, top-three percent ordering, rank/level/skill/gear recording, balance deduction, stale-click protection, save rollback and safe Undo. Real profile untouched.");
    }
}
