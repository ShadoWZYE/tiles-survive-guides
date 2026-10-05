using System.Reflection;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
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
        void Invoke(MainWindow window, string method, params object[] args) => typeof(MainWindow)
            .GetMethod(method, BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, args);
        void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
        var window = Create(); // Exercises XAML initialization and both mode-picker event handlers.
        var heroes = (List<Hero>)typeof(MainWindow).GetField("_heroes", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!;
        var becca = heroes.Single(h => h.Name == "Becca");
        Check(becca.IsOwned && becca.Progress.Current is null, "Old profile lost ownership / invented stars");
        ((TabControl)window.FindName("InspectorTabs")).SelectedIndex = 3;
        Invoke(window, "HeroCard_Click", new Button { Tag = becca }, new RoutedEventArgs());
        Check(becca.IsOwned, "Selecting hero to edit stars changed ownership");
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
        Check(focus.Text.StartsWith("1. Becca") && focus.Text.Contains("2. Rosie") && focus.Text.Contains("3. Ray"), "Wrong balanced guide");
        Check(focus.Text.Contains("Target reached: Becca"), "Guide missing reached target");
        ((ComboBox)window.FindName("FormationModePicker")).SelectedIndex = 2;
        Check(((ComboBox)window.FindName("ModePicker")).SelectedIndex == 2 && focus.Text.StartsWith("1. Rosie"), "Formation mode picker not synchronized");
        window.Close();
        var reopened = Create();
        Invoke(reopened, "SetActiveHero", ((List<Hero>)typeof(MainWindow).GetField("_heroes", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(reopened)!).Single(h => h.Name == "Becca"));
        Check(((TextBox)reopened.FindName("CurrentStars")).Text == "4", "Stars missing after reopen");
        reopened.Close();
        app.Shutdown();
        Console.WriteLine("WPF UI regression passed: startup, legacy save, ownership, star validation/persistence, formation priorities and mode switching. Real profile untouched.");
    }
}
