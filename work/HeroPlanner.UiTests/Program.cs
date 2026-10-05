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
            Invoke(window, "HeroCard_Click", new Button { Tag = heroes.Single(h => h.Name == name) }, new RoutedEventArgs());
        var focus = (TextBlock)window.FindName("FormationResourceFocus");
        Check(focus.Text.Contains("Record these builds"), "Unknown builds must not receive a guessed ranking");
        var data = Field<UpgradeData>(window, "_upgradeData");
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
        ((ComboBox)window.FindName("FormationModePicker")).SelectedIndex = 2;
        Check(((ComboBox)window.FindName("ModePicker")).SelectedIndex == 2 && focus.Text.Contains("per 100 resource units"), "Formation mode picker not synchronized");
        Invoke(window, "EditBuild_Click", new Button { Tag = becca }, new RoutedEventArgs());
        Field<TextBox>(window, "_levelEditor").Text = "2";
        Field<ComboBox>(window, "_targetedPoolEditor").SelectedIndex = 1;
        Check(focus.Text.Contains("TARGETED DRAFT") && focus.Text.Contains("Provisional target"), "Targeted recommendation missing");
        Check(Field<UpgradeSettings>(window, "_upgradeSettings").TargetedPool == "newbie_recuit_up_1", "Pool choice not autosaved");
        Field<Slider>(window, "_starSlider").Value = 5;
        Check(Field<Dictionary<string, HeroBuild>>(window, "_heroBuilds")[becca.AssetSlug].Stage == data.Heroes[becca.AssetSlug].Stages[5].Id, "Star slider did not autosave exact partial rank");
        Check(Field<TextBlock>(window, "_starSliderLabel").Text.Contains("step 5/6"), "Partial-rank label missing");
        Check(Field<StackPanel>(window, "_starPreview").Children.Count == 5, "Star preview must have five slots");
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
        Console.WriteLine("WPF UI regression passed: startup, legacy profile, click-to-own/unown, isolated edit overlay, immediate autosave, invalid-save protection, native persistence and data-driven comparisons. Real profile untouched.");
    }
}
