using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow
{
    private sealed record RecordedUpgrade(string Slug, HeroBuild Before, HeroBuild After,
        Dictionary<string, double> BeforeInventory, Dictionary<string, double> AfterInventory);
    private RecordedUpgrade? _lastRecordedUpgrade;

    private static TextBox Selectable(string text, bool heading = false, Brush? color = null) => new()
    {
        Text = text, IsReadOnly = true, TextWrapping = TextWrapping.Wrap, Background = Brushes.Transparent,
        BorderThickness = new Thickness(0), Padding = new Thickness(0), Foreground = color ?? Brushes.White,
        FontSize = heading ? 14 : 12, FontWeight = heading ? FontWeights.Bold : FontWeights.Normal,
        Margin = new Thickness(0, 3, 0, 6), IsReadOnlyCaretVisible = true,
        HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
    };
    private string CostText(UpgradeCandidate c) => c.Cost.Count == 0 ? "Cost not listed; not assumed free" :
        string.Join(" + ", c.Cost.Select(x => $"{x.Value:0.##} {_upgradeData.Items.GetValueOrDefault(x.Key) ?? x.Key}"));
    private bool HasKnownShortfall(UpgradeCandidate c) => c.Cost.Any(x => _upgradeSettings.Inventory.TryGetValue(x.Key, out double held) && held < x.Value);
    private void ResourceFilter_Changed(object sender, SelectionChangedEventArgs e) => RefreshResourcePriority();
    private string ResourceClass(string? id)
    {
        if (id is "hero-xp" or "gear-xp") return id;
        if (id is null) return "other";
        if (_upgradeData.Heroes.Values.Any(h => h.Stages.Any(s => s.Cost.ContainsKey(id)))) return "rank";
        if (_upgradeData.Heroes.Values.Any(h => h.Skills.Any(s => s.Levels.Any(l => l.Cost.ContainsKey(id))))) return "skill";
        return "other";
    }
    private void RefreshResourcePriority()
    {
        if (ResourcePriorityCards is null || TargetedResourceText is null || ResourceModelLimits is null) return;
        ResourcePriorityCards.Children.Clear(); ResourceModelLimits.Text = UpgradeCaveats;
        UndoUpgradeButton.IsEnabled = _lastRecordedUpgrade is not null;
        TargetedResourceText.Text = _selected.Count == 5 ? TargetedSummary() : "Choose a five-hero formation first.";
        if (_selected.Count != 5) { FormationResourceFocus.Text = "Select five heroes, then record their current builds using the edit buttons."; return; }
        var result = UpgradeModel.Evaluate(_selected.Select(h => h.AssetSlug), _heroBuilds, _upgradeData, _upgradeSettings);
        if (result.Missing.Count > 0) { FormationResourceFocus.Text = "Record these builds first:\n" + string.Join("\n", result.Missing); return; }
        FormationResourceFocus.Text = $"Metric: {_upgradeSettings.Goal} · Client {_upgradeData.ClientBuild}\nTop 3 per individual resource, by formation % increase. Efficiency per 100 resource units is separate. Select and copy any text.";
        string filter = (ResourceClassFilter.SelectedItem as ComboBoxItem)?.Tag as string ?? "all";
        int groups = 0;
        foreach (var group in result.Candidates.Where(c => filter == "all" || ResourceClass(c.Group) == filter)
            .GroupBy(c => c.Group ?? "mixed:" + string.Join("+", c.Cost.Keys.Order())))
        {
            groups++;
            var content = new StackPanel();
            var ordered = group.OrderByDescending(c => c.Gain ?? double.NegativeInfinity).ThenByDescending(c => c.Efficiency ?? double.NegativeInfinity).ThenBy(c => c.Label, StringComparer.Ordinal).ToList();
            var top = ordered.Where(c => c.Blocked is null && c.Gain is not null).Take(3).ToList();
            string resourceName = group.Key.StartsWith("mixed:", StringComparison.Ordinal) ?
                (group.First().Cost.Count == 0 ? "Unlisted costs" : "Mixed: " + string.Join(" + ", group.First().Cost.Keys.Order().Select(id => _upgradeData.Items.GetValueOrDefault(id) ?? id))) :
                _upgradeData.Items.GetValueOrDefault(group.Key) ?? group.Key;
            ResourcePriorityCards.Children.Add(new Expander { Header = $"{resourceName} · top {top.Count}",
                IsExpanded = true, Content = content, Foreground = Brushes.White, Margin = new Thickness(0, 8, 0, 4) });
            int rank = 0; var locked = new StackPanel();
            foreach (var c in ordered.OrderBy(c => top.Contains(c) ? 0 : 1))
            {
                var card = new StackPanel();
                var border = new Border { Child = card, Background = new SolidColorBrush(Color.FromRgb(20, 39, 65)),
                    CornerRadius = new CornerRadius(8), Padding = new Thickness(10), Margin = new Thickness(0, 6, 0, 0) };
                bool eligible = c.Blocked is null && !HasKnownShortfall(c);
                card.Children.Add(Selectable((top.Contains(c) ? $"{++rank}. " : c.Blocked is null ? "Other · " : "Locked · ") + c.Label, true));
                card.Children.Add(Selectable(c.Gain is double gain ? $"Formation gain: {gain:0.####}%" + (c.Efficiency is double e ? $"  |  Return / 100: {e:0.####}%" : "  |  Not comparable") : "Return not modeled (not assumed worthless)", color: Brushes.LightGreen));
                string balances = string.Join("; ", c.Cost.Select(x => _upgradeSettings.Inventory.TryGetValue(x.Key, out double held) ?
                    $"{_upgradeData.Items.GetValueOrDefault(x.Key) ?? x.Key}: {held:0.##} held" : $"{_upgradeData.Items.GetValueOrDefault(x.Key) ?? x.Key}: unknown"));
                card.Children.Add(Selectable($"Cost: {CostText(c)}\nBalance: {c.Affordability}" + (balances.Length > 0 ? " · " + balances : "")));
                if (c.Blocked is not null || HasKnownShortfall(c)) card.Children.Add(Selectable(c.Blocked ?? "Recorded balance is too low. Update it after obtaining materials.", color: Brushes.Gold));
                var details = c.Detail + (c.Delta is { } d ? $"\nATK +{d[0]:0.##} · DEF +{d[1]:0.##} · HP +{d[2]:0.##}" : "") +
                    "\nResource IDs: " + (c.Cost.Count == 0 ? "unlisted" : string.Join(", ", c.Cost.Keys));
                card.Children.Add(new Expander { Header = "Details / requirements", Content = Selectable(details), Foreground = Brushes.White });
                var actions = new WrapPanel { Margin = new Thickness(0, 8, 0, 0) }; card.Children.Add(actions);
                var record = new Button { Content = "Record completed", Tag = c, IsEnabled = eligible, Padding = new Thickness(10, 6, 10, 6),
                    ToolTip = "Confirm you have already completed this exact upgrade in the game. Updates the saved planner build and deducts known balances; unknown balances stay unknown." };
                System.Windows.Automation.AutomationProperties.SetName(record, "Record completed: " + c.Label);
                record.Click += RecordUpgrade_Click; actions.Children.Add(record);
                var edit = new Button { Content = "Edit build / balances", Tag = _heroes.Find(h => h.AssetSlug == c.Slug), Padding = new Thickness(10, 6, 10, 6), Margin = new Thickness(6, 0, 0, 0) };
                edit.Click += EditBuild_Click; actions.Children.Add(edit);
                (top.Contains(c) ? content : locked).Children.Add(border);
            }
            if (locked.Children.Count > 0) content.Children.Add(new Expander { Header = $"Other / locked / unmodeled ({locked.Children.Count})", Content = locked, Foreground = Brushes.Gold, Margin = new Thickness(0, 8, 0, 0) });
        }
        if (groups == 0) ResourcePriorityCards.Children.Add(Selectable("No next upgrades match this resource class / affordability filter."));
        if (result.Notes.Count > 0) ResourcePriorityCards.Children.Add(new Expander { Header = "Excluded / unknown build data", Content = Selectable(string.Join("\n", result.Notes.Distinct())), Foreground = Brushes.White, Margin = new Thickness(0, 8, 0, 0) });
    }
    private static bool SameBuild(HeroBuild? a, HeroBuild? b) => a is not null && b is not null &&
        a.Stage == b.Stage && a.Level == b.Level && (a.Skills ?? []).OrderBy(x => x.Key).SequenceEqual((b.Skills ?? []).OrderBy(x => x.Key)) &&
        (a.Gear is null) == (b.Gear is null) && (a.Gear ?? []).OrderBy(x => x.Id).Select(x => (x.Id, x.Level)).SequenceEqual((b.Gear ?? []).OrderBy(x => x.Id).Select(x => (x.Id, x.Level)));
    private static bool SameBalances(Dictionary<string, double> a, Dictionary<string, double> b) => a.OrderBy(x => x.Key).SequenceEqual(b.OrderBy(x => x.Key));
    private void RecordUpgrade_Click(object sender, RoutedEventArgs e)
    {
        e.Handled = true;
        if (sender is not Button { Tag: UpgradeCandidate requested }) return;
        if (BuildOverlay.Visibility == Visibility.Visible) { UpgradeActionStatus.Text = "Close the build editor before recording an upgrade."; return; }
        if (!SameBuild(_heroBuilds.GetValueOrDefault(requested.Slug), requested.Before))
        { UpgradeActionStatus.Text = "This upgrade card is out of date. Use the refreshed list."; RefreshResourcePriority(); return; }
        // Re-evaluate rather than trust an old button, stale cost or a changed eligibility condition.
        var fresh = UpgradeModel.Evaluate(_selected.Select(h => h.AssetSlug), _heroBuilds, _upgradeData, _upgradeSettings).Candidates
            .Find(c => c.Slug == requested.Slug && c.Label == requested.Label && SameBuild(c.After, requested.After));
        if (_selected.Count != 5 || fresh is null || fresh.Blocked is not null || fresh.After is null || HasKnownShortfall(fresh))
        { UpgradeActionStatus.Text = "Cannot record this upgrade. Check the current build, rank caps and balances."; return; }
        var before = _heroBuilds[fresh.Slug].Copy(); var beforeInventory = new Dictionary<string, double>(_upgradeSettings.Inventory);
        try
        {
            _heroBuilds[fresh.Slug] = fresh.After.Copy();
            foreach (var (id, cost) in fresh.Cost) if (_upgradeSettings.Inventory.ContainsKey(id)) _upgradeSettings.Inventory[id] -= cost;
            SaveProfile();
            _lastRecordedUpgrade = new(fresh.Slug, before, fresh.After.Copy(), beforeInventory, new(_upgradeSettings.Inventory));
            UpgradeActionStatus.Text = "Recorded: " + fresh.Label + ". Saved locally; no game action was sent.";
            RefreshUpgradeViews();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        { _heroBuilds[fresh.Slug] = before; _upgradeSettings.Inventory = beforeInventory; UpgradeActionStatus.Text = "Not recorded: " + ex.Message; }
    }
    private void UndoUpgrade_Click(object sender, RoutedEventArgs e)
    {
        e.Handled = true; var undo = _lastRecordedUpgrade; if (undo is null) return;
        if (BuildOverlay.Visibility == Visibility.Visible || !SameBuild(_heroBuilds.GetValueOrDefault(undo.Slug), undo.After) || !SameBalances(_upgradeSettings.Inventory, undo.AfterInventory))
        { UpgradeActionStatus.Text = "Undo unavailable: close the editor, or the build/balances changed after recording. No data was overwritten."; return; }
        try
        {
            _heroBuilds[undo.Slug] = undo.Before.Copy(); _upgradeSettings.Inventory = new(undo.BeforeInventory); SaveProfile();
            _lastRecordedUpgrade = null; UpgradeActionStatus.Text = "Last recorded upgrade undone; build and balances restored."; RefreshUpgradeViews();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        { _heroBuilds[undo.Slug] = undo.After.Copy(); _upgradeSettings.Inventory = new(undo.AfterInventory); UpgradeActionStatus.Text = "Could not undo: " + ex.Message; }
    }
}
