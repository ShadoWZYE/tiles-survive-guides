using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow
{
    private readonly Dictionary<string, int> _researchEdits = [];
    private string _researchTree = "4300006", _researchSearch = "";
    private bool _researchRecordedOnly, _researchChangedOnly;
    private bool _showGatedResearch;

    private static string ResearchEffects(ArmyContextLevel? row) => row is null ? "Unknown / not recorded — excluded from estimates" :
        string.Join(" / ", row.Effects.Select(e => $"{(e.Scope == "all" ? "All heroes" : e.Scope)} · {new[] { "ATK", "DEF", "HP" }[e.Stat]} +{e.Value:N0}" + (e.Scene == "all" ? "" : $" ({e.Scene.ToUpperInvariant()})")));

    private void RenderResearch()
    {
        var panel = ResearchPanel; panel.Children.Clear();
        panel.Children.Add(CopyText("Research", true));
        panel.Children.Add(CopyText("Match the icon, branch and numbered research to your game. Legacy technology is excluded. Faction Power branches exist in the client files behind feature and Special Forces prerequisites; live availability is unconfirmed. They are hidden by default. Record them only if you can match them in-game."));
        var gated = new CheckBox { Content="Show gated client branches (availability unconfirmed)", IsChecked=_showGatedResearch, Foreground=Brushes.White, Margin=new Thickness(0,6,0,10) };panel.Children.Add(gated);
        gated.Click+=(_,_)=>{_showGatedResearch=gated.IsChecked==true;if(!_showGatedResearch&&_armyContextData.ResearchTrees.GetValueOrDefault(_researchTree)?.Gated==true)_researchTree="4300006";RenderResearch();};
        var toolbar = new WrapPanel(); panel.Children.Add(toolbar);
        var tree = new ComboBox { Width = 210 }; tree.Items.Add(new ComboBoxItem { Content = "All branches", Tag = "all" }); tree.SelectedIndex = 0;
        foreach (var (key, value) in _armyContextData.ResearchTrees.Where(x=>!x.Value.Legacy&&(_showGatedResearch||!x.Value.Gated)).OrderBy(x => x.Value.Order))
        {
            var item = new ComboBoxItem { Content = value.Name + (value.Gated ? " · gated" : ""), Tag = key,ToolTip=value.AvailabilityNote }; tree.Items.Add(item);
            if (key == _researchTree) tree.SelectedItem = item;
        }
        Field(toolbar, "Research branch", tree);
        var search = new TextBox { Width = 240, Text = _researchSearch, ToolTip = "Name, faction, ATK, DEF or HP" }; Field(toolbar, "Find research", search);
        var recorded = new CheckBox { Content = "Recorded only", IsChecked = _researchRecordedOnly, Foreground = Brushes.White, Margin = new Thickness(10, 24, 10, 0) }; toolbar.Children.Add(recorded);
        var changed = new CheckBox { Content = "Changed only", IsChecked = _researchChangedOnly, Foreground = Brushes.White, Margin = new Thickness(10, 24, 10, 0) }; toolbar.Children.Add(changed);
        var savebar = new WrapPanel { Margin = new Thickness(0, 8, 0, 8) }; panel.Children.Add(savebar);
        var save = new Button { Content = "Save Research", Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(0, 0, 10, 0) }; savebar.Children.Add(save);
        var discard = new Button { Content = "Discard edits", Padding = new Thickness(12, 7, 12, 7) }; savebar.Children.Add(discard);
        var progress = CopyText(""); progress.Margin = new Thickness(12, 8, 0, 0); savebar.Children.Add(progress);
        panel.Children.Add(CopyText(_armyContext.Enabled ? "Army context is ON. Bonuses follow the selected encounter and comparison mode." : "Army context is OFF. Record levels now and enable them in Army Setup when ready."));
        panel.Children.Add(CopyText("Edits stay here while switching tabs. Save Research before closing the planner. No prerequisite levels are filled automatically."));
        var status = CopyText(""); panel.Children.Add(status);
        var area = ResearchCardsPanel; area.Children.Clear();
        int Value(string key) => _researchEdits.TryGetValue(key, out int n) ? n : _armyContext.Research.GetValueOrDefault(key);
        int shown = 0;
        void Summary()
        {
            progress.Text = $"{_armyContextData.Research.Keys.Count(k => Value(k) > 0)} / {_armyContextData.Research.Count} recorded · {shown} shown · {_researchEdits.Count} unsaved edits";
            save.IsEnabled = discard.IsEnabled = _researchEdits.Count > 0;
        }
        void Draw()
        {
            area.Children.Clear(); shown = 0;
            var rows = _armyContextData.Research.Where(x =>
                (!_armyContextData.ResearchTrees[x.Value.Tree].Legacy&&(_showGatedResearch||!_armyContextData.ResearchTrees[x.Value.Tree].Gated)) &&
                (_researchTree == "all" || x.Value.Tree == _researchTree) &&
                (!_researchRecordedOnly || Value(x.Key) > 0) && (!_researchChangedOnly || _researchEdits.ContainsKey(x.Key)) &&
                (x.Key + " " + x.Value.Name + " " + ResearchEffects(x.Value.Levels[0])).Contains(_researchSearch.Trim(), StringComparison.OrdinalIgnoreCase))
                .OrderBy(x => _armyContextData.ResearchTrees[x.Value.Tree].Order).ThenBy(x => x.Value.Tier).ThenBy(x => x.Value.Row).ThenBy(x => x.Value.Name);
            string group = ""; WrapPanel? cards = null;
            foreach (var (key, entry) in rows)
            {
                shown++;
                string section = entry.Tree + ":" + entry.Tier;
                if (group != section)
                {
                    group = section; area.Children.Add(CopyText(_armyContextData.ResearchTrees[entry.Tree].Name + " · Tier " + entry.Tier, true));
                    cards = new WrapPanel(); area.Children.Add(cards);
                }
                var body = new StackPanel();
                var card = new Border { Child = body, Width = 360, Padding = new Thickness(12), Margin = new Thickness(0, 6, 12, 6), Background = new SolidColorBrush(Color.FromRgb(27, 52, 86)), CornerRadius = new CornerRadius(10) }; cards!.Children.Add(card);
                var heading = new DockPanel(); body.Children.Add(heading); heading.Children.Add(ContextIcon(entry.IconAsset, 56)); heading.Children.Add(CopyText(entry.Name, true));
                var controls = new DockPanel { Margin = new Thickness(0, 10, 0, 8) }; body.Children.Add(controls);
                var minus = new Button { Content = "−", Width = 34, Padding = new Thickness(4), Margin = new Thickness(0, 0, 6, 0) }; controls.Children.Add(minus);
                var plus = new Button { Content = "+", Width = 34, Padding = new Thickness(4), Margin = new Thickness(6, 0, 0, 0) }; DockPanel.SetDock(plus, Dock.Right); controls.Children.Add(plus);
                var picker = new ComboBox(); picker.Items.Add(new ComboBoxItem { Content = "Unknown / not recorded", Tag = 0 }); picker.SelectedIndex = 0;
                foreach (var row in entry.Levels) { var item = new ComboBoxItem { Content = $"Level {row.Level} / {entry.Levels.Last().Level}", Tag = row.Level }; picker.Items.Add(item); if (Value(key) == row.Level) picker.SelectedItem = item; }
                System.Windows.Automation.AutomationProperties.SetName(picker, "Research node " + key); controls.Children.Add(picker);
                var preview = CopyText(""); body.Children.Add(preview);
                var note = CopyText(""); note.Foreground = Brushes.Gold; body.Children.Add(note);
                void Describe()
                {
                    var row = entry.Levels.Find(r => r.Level == (int)((ComboBoxItem)picker.SelectedItem).Tag);
                    preview.Text = ResearchEffects(row) + (row?.Unmodeled.Count > 0 ? "\nAdditional node effects are excluded from the score." : "");
                    note.Text = _researchEdits.ContainsKey(key) ? "Unsaved change" : "";
                }
                picker.SelectionChanged += (_, _) => { int n = (int)((ComboBoxItem)picker.SelectedItem).Tag; if (n == _armyContext.Research.GetValueOrDefault(key)) _researchEdits.Remove(key); else _researchEdits[key] = n; Describe(); Summary(); };
                minus.Click += (_, _) => picker.SelectedIndex = Math.Max(0, picker.SelectedIndex - 1);
                plus.Click += (_, _) => picker.SelectedIndex = Math.Min(picker.Items.Count - 1, picker.SelectedIndex + 1);
                Describe();
            }
            if (shown == 0) area.Children.Add(CopyText("No matching research. Try another branch or clear the filters."));
            Summary();
        }
        tree.SelectionChanged += (_, _) => { _researchTree = (string)((ComboBoxItem)tree.SelectedItem).Tag; Draw(); };
        search.TextChanged += (_, _) => { _researchSearch = search.Text; Draw(); };
        recorded.Click += (_, _) => { _researchRecordedOnly = recorded.IsChecked == true; Draw(); };
        changed.Click += (_, _) => { _researchChangedOnly = changed.IsChecked == true; Draw(); };
        save.Click += (_, _) => {
            var next = CopyContext(); foreach (var (key, n) in _researchEdits) { if (n > 0) next.Research[key] = n; else next.Research.Remove(key); }
            if (SaveContextSelection(next, status)) { _researchEdits.Clear(); Draw(); }
        };
        discard.Click += (_, _) => { _researchEdits.Clear(); Draw(); status.Text = "Edits discarded. Saved levels were kept."; };
        Draw();
    }

    private void ResearchEdits_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (_researchEdits.Count == 0) return;
        var choice = MessageBox.Show(this, "Save your Research edits before closing?", "Unsaved Research", MessageBoxButton.YesNoCancel, MessageBoxImage.Question);
        if (choice == MessageBoxResult.Cancel) { e.Cancel = true; return; }
        if (choice == MessageBoxResult.Yes)
        {
            var next = CopyContext(); foreach (var (key, n) in _researchEdits) { if (n > 0) next.Research[key] = n; else next.Research.Remove(key); }
            var status = CopyText(""); if (!SaveContextSelection(next, status)) { MessageBox.Show(this, status.Text, "Could not save Research"); e.Cancel = true; return; }
        }
        _researchEdits.Clear();
    }

    private void ArmySetup_Click(object sender, RoutedEventArgs e)
    {
        var window = new Window { Title = "Army Setup", Owner = this, Width = 740, Height = 660, MinWidth = 560, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = new SolidColorBrush(Color.FromRgb(16, 36, 62)), Foreground = Brushes.White };
        var panel = new StackPanel { Margin = new Thickness(22) }; window.Content = new ScrollViewer { Content = panel, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        panel.Children.Add(CopyText("Army Setup", true)); panel.Children.Add(CopyText("Record what you have, then choose whether those bonuses are included in comparisons."));
        var enabled = new CheckBox { Content = "Include recorded army bonuses", IsChecked = _armyContext.Enabled, Foreground = Brushes.White, Margin = new Thickness(0, 12, 0, 8) }; panel.Children.Add(enabled);
        var scene = new ComboBox { Width = 200, HorizontalAlignment = HorizontalAlignment.Left };
        foreach (var (key, label) in new[] { ("all", "General / PvP"), ("pve", "PvE"), ("gve", "GVE") }) { var item = new ComboBoxItem { Content = label, Tag = key }; scene.Items.Add(item); if (key == _armyContext.Scene) scene.SelectedItem = item; } panel.Children.Add(scene);
        var status = CopyText("");
        bool Apply() { var next = CopyContext(); next.Enabled = enabled.IsChecked == true; next.Scene = (string)((ComboBoxItem)scene.SelectedItem).Tag; bool saved = SaveContextSelection(next, status); if(saved && InspectorTabs.SelectedIndex==6) RenderResearch(); return saved; }
        void Section(string title, string summary, string action, string nav)
        {
            var body = new StackPanel(); panel.Children.Add(new Border { Child = body, Padding = new Thickness(12), Margin = new Thickness(0, 12, 0, 0), Background = new SolidColorBrush(Color.FromRgb(27, 52, 86)), CornerRadius = new CornerRadius(10) });
            body.Children.Add(CopyText(title, true)); body.Children.Add(CopyText(summary));
            var button = new Button { Content = action, HorizontalAlignment = HorizontalAlignment.Left, Padding = new Thickness(12, 6, 12, 6) }; body.Children.Add(button);
            button.Click += (_, _) => { if (!Apply()) return; window.Close(); Navigation_Click(FindName(nav), new RoutedEventArgs()); };
        }
        Section("Research", $"{_armyContext.Research.Count} / {_armyContextData.Research.Count} nodes recorded", "Configure Research", "ResearchNav");
        Section("Signature Gear", $"{_armyContext.Signature.Count} heroes recorded · applies in My builds", "Configure hero gear", "RosterNav");
        Section("Behemoths", _armyContext.BehemothSource == "configured" ? $"{_armyContext.BehemothBuilds.Count} configured Behemoths" : "Manual hero-bonus snapshot", "Configure Behemoths", "BehemothsNav");
        panel.Children.Add(CopyText("Partial stat model. Linked Signature skills, Behemoth combat skills and troop multipliers remain excluded. Max heroes (no gear) ignores army bonuses."));
        panel.Children.Add(status); var buttons = new WrapPanel(); panel.Children.Add(buttons);
        foreach (string label in new[] { "Save settings", "Detailed editor", "Close" })
        {
            var button = new Button { Content = label, Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(0, 6, 8, 0) }; buttons.Children.Add(button);
            button.Click += (_, _) => { if (label == "Save settings") Apply(); else if (label == "Detailed editor") { window.Close(); ArmyContext_Click(sender, e); } else window.Close(); };
        }
        window.ShowDialog();
    }
}
