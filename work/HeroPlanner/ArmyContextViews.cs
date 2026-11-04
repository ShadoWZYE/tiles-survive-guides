using System.Globalization;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow
{
    private static Image ContextIcon(string asset, int size) => new()
    {
        Source = new BitmapImage(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Images/ContextIcons/" + asset + ".png")),
        Width = size, Height = size, Stretch = Stretch.Uniform,
        Margin = new Thickness(0, 0, 12, 0), VerticalAlignment = VerticalAlignment.Top
    };

    private static string ContextStats(ArmyContextLevel? row)
    {
        double[] stats = [0, 0, 0];
        foreach (var effect in row?.Effects ?? []) if (effect.Scope == "all" && effect.Scene == "all") stats[effect.Stat] += effect.Value;
        return string.Join(" · ", stats.Select((v, i) => $"{new[] { "ATK", "DEF", "HP" }[i]} +{v:N0}"));
    }

    private bool SaveContextSelection(ArmyContextSettings next, TextBlock status)
    {
        var old = _armyContext;
        _armyContext = ArmyContextModel.Clean(next, _armyContextData);
        try { SaveProfile(); }
        catch (Exception ex) { _armyContext = old; status.Text = "Not saved: " + ex.Message; return false; }
        RefreshEstimates(); RebuildOptimizer(); UpdateRecommendations(); UpdateSquadPresentation();
        if (_activeHero is not null) RefreshSignaturePanels(_activeHero);
        status.Text = "Saved locally. Context applies according to the selected comparison mode.";
        return true;
    }

    private ArmyContextSettings CopyContext() => JsonSerializer.Deserialize<ArmyContextSettings>(JsonSerializer.Serialize(_armyContext))!;

    private void RefreshSignaturePanels(Hero hero)
    {
        foreach (var panel in new[] { StatsSignaturePanel, SkillsSignaturePanel, RosterSignaturePanel })
        { panel.Children.Clear(); panel.Children.Add(CreateSignaturePanel(hero.AssetSlug)); }
    }

    private FrameworkElement CreateSignaturePanel(string slug)
    {
        var body = new StackPanel();
        var card = new Border { Child = body, Background = new SolidColorBrush(Color.FromRgb(27, 52, 86)), CornerRadius = new CornerRadius(10), Padding = new Thickness(12), Margin = new Thickness(0, 10, 0, 10) };
        if (!_armyContextData.Signature.TryGetValue(slug, out var entry))
        { body.Children.Add(CopyText("Signature Gear — no entry for this hero in the data snapshot.")); return card; }
        var heading = new DockPanel(); body.Children.Add(heading);
        heading.Children.Add(ContextIcon(entry.IconAsset, 64)); heading.Children.Add(CopyText("Signature Gear · " + entry.Name, true));
        var picker = new ComboBox { MinWidth = 170, HorizontalAlignment = HorizontalAlignment.Left, Margin = new Thickness(0, 8, 0, 6) };
        System.Windows.Automation.AutomationProperties.SetName(picker, "Hero Signature Gear level " + slug);
        picker.Items.Add(new ComboBoxItem { Content = "Unknown / excluded", Tag = 0 }); picker.SelectedIndex = 0;
        foreach (var row in entry.Levels)
        {
            var item = new ComboBoxItem { Content = "Level " + row.Level, Tag = row.Level }; picker.Items.Add(item);
            if (_armyContext.Signature.GetValueOrDefault(slug) == row.Level) picker.SelectedItem = item;
        }
        body.Children.Add(picker);
        var stats = CopyText(""); body.Children.Add(stats);
        var skillHeading = new DockPanel { Margin = new Thickness(0, 8, 0, 4) }; body.Children.Add(skillHeading);
        skillHeading.Children.Add(ContextIcon(entry.SkillIconAsset, 42)); skillHeading.Children.Add(CopyText(entry.SkillName, true));
        var description = CopyText(""); body.Children.Add(description);
        void Describe()
        {
            var row = entry.Levels.Find(r => r.Level == (int)((ComboBoxItem)picker.SelectedItem).Tag);
            stats.Text = row is null ? "Choose the current level; unknown gear remains excluded." : ContextStats(row);
            description.Text = (row ?? entry.Levels[0]).Description;
        }
        picker.SelectionChanged += (_, _) => Describe(); Describe();
        body.Children.Add(CopyText("Client skill description. Linked damage/skill effects remain unverified and excluded. Flat gear stats apply only in My builds with army context enabled."));
        var enabled = new CheckBox { Content = "Apply army context (Research / Behemoth settings included)", IsChecked = _armyContext.Enabled, Foreground = Brushes.White, Margin = new Thickness(0, 8, 0, 4) }; body.Children.Add(enabled);
        var save = new Button { Content = "Save Signature Gear", HorizontalAlignment = HorizontalAlignment.Left, Padding = new Thickness(12, 7, 12, 7) }; body.Children.Add(save);
        var status = CopyText(""); body.Children.Add(status);
        save.Click += (_, e) => {
            e.Handled = true;
            var next = CopyContext(); next.Enabled = enabled.IsChecked == true;
            int n = (int)((ComboBoxItem)picker.SelectedItem).Tag;
            if (n > 0) next.Signature[slug] = n; else next.Signature.Remove(slug);
            SaveContextSelection(next, status);
        };
        return card;
    }

    private void RenderBehemoths()
    {
        var panel = BehemothsPanel; panel.Children.Clear();
        panel.Children.Add(CopyText("Behemoths", true));
        panel.Children.Add(CopyText("Bonuses granted to your heroes. Record only Behemoths whose benefits apply to this march. Skills, talents and own combat damage remain excluded."));
        var enabled = new CheckBox { Content = "Apply army context", IsChecked = _armyContext.Enabled, Foreground = Brushes.White, Margin = new Thickness(0, 8, 0, 8) }; panel.Children.Add(enabled);
        var source = new ComboBox { HorizontalAlignment = HorizontalAlignment.Left, MinWidth = 300 };
        source.Items.Add(new ComboBoxItem { Content = "Manual combined hero bonuses", Tag = "manual" });
        source.Items.Add(new ComboBoxItem { Content = "Configured level + star base bonuses", Tag = "configured" });
        source.SelectedIndex = _armyContext.BehemothSource == "configured" ? 1 : 0;
        System.Windows.Automation.AutomationProperties.SetName(source, "Behemoth bonus source"); panel.Children.Add(source);
        var manualPanel = new WrapPanel(); panel.Children.Add(manualPanel); var inputs = new List<TextBox>();
        for (int i = 0; i < 3; i++)
        {
            var input = new TextBox { Width = 125, Text = _armyContext.Behemoth[i]?.ToString(CultureInfo.InvariantCulture) ?? "" };
            Field(manualPanel, new[] { "ATK bonus", "DEF bonus", "HP bonus" }[i], input); inputs.Add(input);
        }
        panel.Children.Add(CopyText("The selected source is used once. Manual and configured bonuses never stack. Manual fields are hero bonuses, not the Behemoth’s own stats."));
        var levels = new Dictionary<string, ComboBox>(); var stars = new Dictionary<string, ComboBox>();
        var cards = new System.Windows.Controls.Primitives.UniformGrid { Columns = 2 }; panel.Children.Add(cards);
        foreach (var (key, entry) in _armyContextData.Behemoths)
        {
            var body = new StackPanel();
            cards.Children.Add(new Border { Child = body, Padding = new Thickness(12), CornerRadius = new CornerRadius(10), Background = new SolidColorBrush(Color.FromRgb(27, 52, 86)), Margin = new Thickness(0, 10, 12, 0) });
            var header = new DockPanel(); body.Children.Add(header); header.Children.Add(ContextIcon(entry.IconAsset, 76)); header.Children.Add(CopyText(entry.Name, true));
            body.Children.Add(CopyText(entry.AvailabilityNote));
            var pickers = new WrapPanel(); body.Children.Add(pickers);
            ComboBox Picker(string part, List<ArmyContextLevel> rows, int current)
            {
                var picker = new ComboBox { Width = 180 }; picker.Items.Add(new ComboBoxItem { Content = "Unknown / excluded", Tag = 0 }); picker.SelectedIndex = 0;
                foreach (var row in rows) { var item = new ComboBoxItem { Content = (part == "star" ? "Config step " : "Level ") + row.Level, Tag = row.Level }; picker.Items.Add(item); if (current == row.Level) picker.SelectedItem = item; }
                Field(pickers, part == "star" ? "Exact star step" : "Level", picker);
                System.Windows.Automation.AutomationProperties.SetName(picker, "Behemoth " + key + " " + part); return picker;
            }
            var build = _armyContext.BehemothBuilds.GetValueOrDefault(key) ?? new();
            levels[key] = Picker("level", entry.Levels, build.Level); stars[key] = Picker("star", entry.Stars, build.Star);
            var summary = CopyText(""); body.Children.Add(summary);
            void Describe() => summary.Text = ContextStats(entry.Levels.Find(r => r.Level == (int)((ComboBoxItem)levels[key].SelectedItem).Tag)) + "\n" + ContextStats(entry.Stars.Find(r => r.Level == (int)((ComboBoxItem)stars[key].SelectedItem).Tag));
            levels[key].SelectionChanged += (_, _) => Describe(); stars[key].SelectionChanged += (_, _) => Describe(); Describe();
            body.Children.Add(CopyText("Star step is the exact configuration progression index, not the displayed star count. Leave unknown if it cannot be matched."));
        }
        void SourceState() { bool manual = source.SelectedIndex == 0; foreach (var input in inputs) input.IsEnabled = manual; foreach (var picker in levels.Values.Concat(stars.Values)) picker.IsEnabled = !manual; }
        source.SelectionChanged += (_, _) => SourceState(); SourceState();
        var save = new Button { Content = "Save Behemoths", HorizontalAlignment = HorizontalAlignment.Left, Padding = new Thickness(14, 8, 14, 8), Margin = new Thickness(0, 12, 0, 4) }; panel.Children.Add(save);
        var status = CopyText(""); panel.Children.Add(status);
        save.Click += (_, _) => {
            var next = CopyContext(); next.Enabled = enabled.IsChecked == true; next.BehemothSource = (string)((ComboBoxItem)source.SelectedItem).Tag;
            for (int i = 0; i < 3; i++)
            {
                if(next.BehemothSource != "manual") continue;
                if (string.IsNullOrWhiteSpace(inputs[i].Text)) { next.Behemoth[i] = null; continue; }
                if (!double.TryParse(inputs[i].Text, NumberStyles.Float, CultureInfo.InvariantCulture, out double v) || !double.IsFinite(v) || v < 0 || v > 1e12) { status.Text = "Enter finite, non-negative bonuses or leave blank. Nothing saved."; return; }
                next.Behemoth[i] = v;
            }
            next.BehemothBuilds = levels.ToDictionary(x => x.Key, x => new ArmyBehemothBuild { Level = (int)((ComboBoxItem)x.Value.SelectedItem).Tag, Star = (int)((ComboBoxItem)stars[x.Key].SelectedItem).Tag });
            SaveContextSelection(next, status);
        };
    }
}
