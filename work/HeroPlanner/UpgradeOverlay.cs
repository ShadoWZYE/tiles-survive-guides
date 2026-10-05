using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow
{
    private UpgradeData _upgradeData = new();
    private Dictionary<string, HeroBuild> _heroBuilds = [];
    private UpgradeSettings _upgradeSettings = new();
    private Hero? _editingHero;
    private ComboBox _rankEditor = new(), _stageEditor = new(), _gearModeEditor = new(), _goalEditor = new(), _targetedPoolEditor = new();
    private TextBox _levelEditor = new(), _secondsEditor = new();
    private CheckBox _affordableEditor = new();
    private readonly Dictionary<string, TextBox> _skillEditors = [];
    private readonly Dictionary<string, TextBlock> _skillLabels = [];
    private TextBlock _levelLabel = new();
    private readonly Dictionary<int, (ComboBox Type, TextBox Level)> _gearEditors = [];
    private readonly Dictionary<string, TextBox> _budgetEditors = [];
    private StackPanel _overlayResults = new();
    private IInputElement? _focusBeforeOverlay;
    private bool _populatingEditor;
    private Slider _starSlider = new();
    private StackPanel _starPreview = new();
    private TextBlock _starSliderLabel = new();
    private bool _syncingStarSlider;
    private sealed record Choice(string? Id, string Label) { public override string ToString() => Label; }

    private void LoadUpgradeData()
    {
        var resource = Application.GetResourceStream(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Data/upgrades.json"))
            ?? throw new InvalidDataException("Embedded upgrade data missing.");
        using var reader = new StreamReader(resource.Stream); _upgradeData = UpgradeData.Parse(reader.ReadToEnd());
        ConfigVersionText.Text = "Client config " + _upgradeData.ClientBuild;
        RosterCountText.Text = $"{_heroes.Count} base heroes  •  {_heroes.Count(h => h.HasAscension)} ascended forms";
    }
    private static TextBlock CopyText(string text, bool heading = false) => new()
    {
        Text = text, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 6, 0, 8),
        FontSize = heading ? 16 : 13, FontWeight = heading ? FontWeights.Bold : FontWeights.Normal,
        Foreground = Brushes.White
    };
    private static TextBox NumberEditor(int? value) => new() { Text = value?.ToString(CultureInfo.InvariantCulture) ?? "", Width = 120, Padding = new Thickness(7, 5, 7, 5), FontSize = 14, Margin = new Thickness(0, 0, 12, 8), ToolTip = "Leave blank if unknown." };
    private static TextBlock Field(Panel panel, string label, FrameworkElement control)
    {
        var stack = new StackPanel { Margin = new Thickness(0, 0, 16, 6) };
        var text = CopyText(label); stack.Children.Add(text); stack.Children.Add(control); panel.Children.Add(stack);
        System.Windows.Automation.AutomationProperties.SetName(control, label);
        return text;
    }
    private void CardControl_MouseDown(object sender, MouseButtonEventArgs e)
    {
        // The card's scroll gesture must not capture a checkbox/edit-button gesture.
        _rosterDragPending = false; _rosterDragging = false;
    }
    private void CardOwned_MouseUp(object sender, MouseButtonEventArgs e)
    {
        if (sender is not CheckBox check || check.DataContext is not Hero hero) return;
        hero.IsOwned = !hero.IsOwned;
        check.SetCurrentValue(CheckBox.IsCheckedProperty, hero.IsOwned);
        if (!check.IsLoaded) { SaveProfile(); RefreshOwnedState(); }
        e.Handled = true;
    }
    private void EditBuild_Click(object sender, RoutedEventArgs e)
    {
        e.Handled = true;
        if (sender is not Button { Tag: Hero hero } || !_upgradeData.Heroes.TryGetValue(hero.AssetSlug, out var h)) return;
        _populatingEditor = true;
        EndRosterDrag(); _editingHero = hero; _focusBeforeOverlay = Keyboard.FocusedElement;
        BuildTitle.Text = $"Edit build · {hero.Name}"; BuildFields.Children.Clear(); BuildError.Text = "";
        _skillEditors.Clear(); _skillLabels.Clear(); _gearEditors.Clear(); _budgetEditors.Clear();
        var b = _heroBuilds.GetValueOrDefault(hero.AssetSlug) ?? new();
        BuildFields.Children.Add(CopyText("Valid changes save automatically. Blank = unknown. Skill level 0 = locked."));
        BuildFields.Children.Add(CopyText("Current build", true));
        _starPreview = new StackPanel { Orientation = Orientation.Horizontal };
        _starSliderLabel = CopyText("");
        _starSlider = new Slider { Minimum = -1, Maximum = h.Stages.Count - 1, TickFrequency = 1, IsSnapToTickEnabled = true,
            IsMoveToPointEnabled = true, Width = 490, HorizontalAlignment = HorizontalAlignment.Left, Margin = new Thickness(0, 4, 0, 10),
            ToolTip = "Drag to the exact rank step. Leftmost = unknown. Arrow keys move one step." };
        _starSlider.Value = Math.Max(-1, h.Stages.FindIndex(s => s.Id == b.Stage));
        BuildFields.Children.Add(_starPreview); BuildFields.Children.Add(_starSliderLabel); BuildFields.Children.Add(_starSlider);
        var top = new WrapPanel(); BuildFields.Children.Add(top);
        _rankEditor = new ComboBox { Width = 190, Height = 34, FontSize = 14, ToolTip = "Ranks 1–5 fill purple stars. Ranks 6–10 replace them with gold stars. Step 6 completes a star." };
        _stageEditor = new ComboBox { Width = 190, Height = 34, FontSize = 14 };
        _rankEditor.Items.Add(new Choice(null, "Unknown"));
        foreach (int rank in h.Stages.Select(s => s.Rank).Distinct()) _rankEditor.Items.Add(new Choice(rank.ToString(), rank == 0 ? "0 stars · Rank 0" : rank <= 5 ? $"Purple star {rank} · Rank {rank}" : rank <= 10 ? $"Gold star {rank - 5} · Rank {rank}" : $"Rank {rank}"));
        var currentStage = h.Stages.Find(s => s.Id == b.Stage);
        _rankEditor.SelectedItem = _rankEditor.Items.Cast<Choice>().FirstOrDefault(c => c.Id == currentStage?.Rank.ToString()) ?? _rankEditor.Items[0];
        void UpdateCaps()
        {
            var selected = h.Stages.Find(s => s.Id == (_stageEditor.SelectedItem as Choice)?.Id);
            _levelLabel.Text = selected is null ? "Hero level" : $"Hero level (max {selected.LevelMax})";
            foreach (var skill in h.Skills)
                if (_skillLabels.TryGetValue(skill.Id, out var label)) label.Text = selected is null ? skill.Name : $"{skill.Name} (max {selected.SkillCaps.ElementAtOrDefault(skill.Slot)})";
            if (!_syncingStarSlider)
            {
                _syncingStarSlider = true; _starSlider.Value = selected is null ? -1 : h.Stages.IndexOf(selected); _syncingStarSlider = false;
            }
            DrawRankProgress(selected);
        }
        void Steps()
        {
            bool wasPopulating = _populatingEditor; _populatingEditor = true;
            _stageEditor.Items.Clear(); _stageEditor.Items.Add(new Choice(null, "Unknown"));
            if (int.TryParse((_rankEditor.SelectedItem as Choice)?.Id, out int rank))
                foreach (var s in h.Stages.Where(s => s.Rank == rank)) _stageEditor.Items.Add(new Choice(s.Id, s.Step == 0 ? "No star progress" : s.Step == 6 ? "Step 6/6 · full star" : $"Step {s.Step}/6 · partial"));
            _stageEditor.SelectedItem = _stageEditor.Items.Cast<Choice>().FirstOrDefault(c => c.Id == b.Stage) ?? _stageEditor.Items[0];
            UpdateCaps();
            _populatingEditor = wasPopulating;
            if (!wasPopulating) SaveBuildOnEdit();
        }
        _rankEditor.SelectionChanged += (_, _) => Steps(); _stageEditor.SelectionChanged += (_, _) => UpdateCaps();
        Field(top, "Configured rank", _rankEditor); Field(top, "Rank step", _stageEditor);
        _levelEditor = NumberEditor(b.Level); _levelLabel = Field(top, "Hero level", _levelEditor);
        BuildFields.Children.Add(CopyText("Match the five-star row and partial step to your hero. Step 6 completes that star. Sectors show steps, not fragment-cost percentages."));
        var skills = new WrapPanel(); BuildFields.Children.Add(skills);
        foreach (var skill in h.Skills)
        {
            var editor = NumberEditor((b.Skills ?? []).TryGetValue(skill.Id, out int n) ? n : null);
            var skillPanel = new StackPanel { Width = 190 };
            var gameSkill = hero.Skills.Find(s => s.InternalName == skill.Id);
            if (gameSkill is not null && !string.IsNullOrWhiteSpace(gameSkill.Icon))
                skillPanel.Children.Add(new Image { Source = new BitmapImage(new Uri(gameSkill.Icon)), Width = 38, Height = 38, HorizontalAlignment = HorizontalAlignment.Left, ToolTip = gameSkill.DisplayName });
            _skillEditors[skill.Id] = editor; _skillLabels[skill.Id] = Field(skillPanel, skill.Name, editor);
            skills.Children.Add(skillPanel);
        }
        Steps();
        _starSlider.ValueChanged += (_, _) => {
            if (_syncingStarSlider || _populatingEditor) return;
            var selected = h.Stages.ElementAtOrDefault((int)Math.Round(_starSlider.Value));
            _syncingStarSlider = true; _populatingEditor = true;
            _rankEditor.SelectedItem = _rankEditor.Items.Cast<Choice>().First(c => c.Id == selected?.Rank.ToString());
            _stageEditor.SelectedItem = _stageEditor.Items.Cast<Choice>().First(c => c.Id == selected?.Id);
            _populatingEditor = false; _syncingStarSlider = false;
            UpdateCaps(); SaveBuildOnEdit();
        };
        var locked = new Button { Content = "Fill locked skills with 0", Padding = new Thickness(9, 5, 9, 5), HorizontalAlignment = HorizontalAlignment.Left, ToolTip = "Only fills skills whose cap is 0 at this exact rank step. Other skill levels are unchanged." };
        locked.Click += (_, _) => {
            var stage = h.Stages.Find(s => s.Id == (_stageEditor.SelectedItem as Choice)?.Id);
            if (stage is null) { BuildError.Text = "Choose a rank and step first."; return; }
            foreach (var skill in h.Skills.Where(s => stage.SkillCaps.ElementAtOrDefault(s.Slot) == 0)) _skillEditors[skill.Id].Text = "0";
        };
        BuildFields.Children.Add(locked);
        var gearFields = new StackPanel();
        BuildFields.Children.Add(new Expander { Header = "Optional gear · expand to record", Content = gearFields, Foreground = Brushes.White, Margin = new Thickness(0, 10, 0, 10) });
        _gearModeEditor = new ComboBox { Width = 430, HorizontalAlignment = HorizontalAlignment.Left };
        _gearModeEditor.Items.Add("Unknown / excluded"); _gearModeEditor.Items.Add("Recorded (empty slots mean no gear)");
        _gearModeEditor.SelectedIndex = b.Gear is null ? 0 : 1; Field(gearFields, "Gear recording", _gearModeEditor);
        gearFields.Children.Add(CopyText("Only universal gear types are supported. Profession/exclusive gear and refinement effects are excluded."));
        foreach (int slot in new[] { 1, 2, 3 })
        {
            var row = new WrapPanel(); gearFields.Children.Add(row);
            var type = new ComboBox { Width = 340 }; type.Items.Add(new Choice(null, "None"));
            foreach (var (id, g) in _upgradeData.Gear.Where(x => x.Value.Slot == slot)) type.Items.Add(new Choice(id, $"{g.Name} · quality {g.Quality}"));
            var recorded = b.Gear?.Find(g => g is not null && _upgradeData.Gear.GetValueOrDefault(g.Id)?.Slot == slot);
            type.SelectedItem = type.Items.Cast<Choice>().FirstOrDefault(c => c.Id == recorded?.Id) ?? type.Items[0];
            var level = NumberEditor(recorded?.Level); _gearEditors[slot] = (type, level);
            Field(row, $"Gear slot {slot}", type); Field(row, $"Slot {slot} level", level);
        }
        var comparison = new StackPanel();
        BuildFields.Children.Add(new Expander { Header = "Upgrade comparison · metric, balances and results", Content = comparison, Foreground = Brushes.White, Margin = new Thickness(0, 10, 0, 10) });
        comparison.Children.Add(CopyText("Results use the saved builds of your selected five-hero formation."));
        var metric = new WrapPanel(); comparison.Children.Add(metric);
        _goalEditor = new ComboBox { Width = 300 };
        foreach (var choice in GoalChoices()) _goalEditor.Items.Add(choice);
        _goalEditor.SelectedItem = _goalEditor.Items.Cast<Choice>().First(c => c.Id == _upgradeSettings.Goal);
        Field(metric, "Return metric", _goalEditor); _secondsEditor = NumberEditor(_upgradeSettings.Seconds); Field(metric, "Window (1–300 sec)", _secondsEditor);
        _affordableEditor = new CheckBox { Content = "Only affordable", IsChecked = _upgradeSettings.OnlyAffordable, Margin = new Thickness(0, 25, 0, 0), Foreground = Brushes.White };
        metric.Children.Add(_affordableEditor);
        comparison.Children.Add(CopyText("Targeted Draft · choose the pool matching the heroes offered in-game", true));
        var draftHeader = new WrapPanel(); comparison.Children.Add(draftHeader);
        draftHeader.Children.Add(new Image { Source = new BitmapImage(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Images/sp_icon_item_up_drop_card_npp.png")), Width = 36, Height = 36, Margin = new Thickness(0, 0, 8, 0) });
        _targetedPoolEditor = new ComboBox { Width = 550, MaxWidth = 550, Height = 34 };
        _targetedPoolEditor.Items.Add(new Choice(null, "Choose the in-game pool (not inferred from server age)"));
        foreach (var pool in (_upgradeData.TargetedDraft?.Pools ?? []).DistinctBy(p => string.Join(',', p.Choices.Select(c => c.HeroInternal)) + $"/{p.SingleCost}/{p.Pity}/{p.UnlockLevel}/{p.SelectedHeroChance}/{p.SelectedShardChance}/{p.SelectedBonusChance}"))
            _targetedPoolEditor.Items.Add(new Choice(pool.Id, string.Join(", ", pool.Choices.Select(c => _upgradeData.Heroes.GetValueOrDefault(c.Slug)?.Name ?? c.HeroInternal.Replace("survivor_", "")))));
        _targetedPoolEditor.SelectedItem = _targetedPoolEditor.Items.Cast<Choice>().FirstOrDefault(c => c.Id == _upgradeSettings.TargetedPool) ?? _targetedPoolEditor.Items[0];
        Field(draftHeader, "Available targets", _targetedPoolEditor);
        var budgetPanel = new WrapPanel();
        var slugs = _selected.Select(x => x.AssetSlug).Append(hero.AssetSlug).Distinct();
        var ids = slugs.SelectMany(s => _upgradeData.Heroes[s].Stages.SelectMany(r => r.Cost.Keys).Concat(_upgradeData.Heroes[s].Skills.SelectMany(k => k.Levels.SelectMany(l => l.Cost.Keys)))).Append("hero-xp").Append("gear-xp").Distinct().Order();
        foreach (var id in ids)
        {
            var input = new TextBox { Width = 180, Text = _upgradeSettings.Inventory.TryGetValue(id, out var balance) ? balance.ToString(CultureInfo.InvariantCulture) : "" };
            _budgetEditors[id] = input; Field(budgetPanel, $"{_upgradeData.Items.GetValueOrDefault(id) ?? id} [{id}]", input);
        }
        comparison.Children.Add(new Expander { Header = "Resource balances · blank means unknown", Content = budgetPanel, Foreground = Brushes.White, Margin = new Thickness(0, 10, 0, 10) });
        comparison.Children.Add(CopyText("Metric and balances also save automatically. Invalid entries keep the last valid value."));
        comparison.Children.Add(new Expander { Header = "Model limits / assumptions", Content = CopyText(UpgradeCaveats), Foreground = Brushes.White });
        _overlayResults = new StackPanel(); comparison.Children.Add(_overlayResults);
        _levelEditor.TextChanged += (_, _) => SaveBuildOnEdit();
        _stageEditor.SelectionChanged += (_, _) => SaveBuildOnEdit();
        _gearModeEditor.SelectionChanged += (_, _) => SaveBuildOnEdit();
        foreach (var editor in _skillEditors.Values) editor.TextChanged += (_, _) => SaveBuildOnEdit();
        foreach (var (type, level) in _gearEditors.Values) { type.SelectionChanged += (_, _) => SaveBuildOnEdit(); level.TextChanged += (_, _) => SaveBuildOnEdit(); }
        _goalEditor.SelectionChanged += (_, _) => SaveSettingsOnEdit();
        _secondsEditor.TextChanged += (_, _) => SaveSettingsOnEdit();
        _targetedPoolEditor.SelectionChanged += (_, _) => SaveSettingsOnEdit();
        _affordableEditor.Checked += (_, _) => SaveSettingsOnEdit(); _affordableEditor.Unchecked += (_, _) => SaveSettingsOnEdit();
        foreach (var editor in _budgetEditors.Values) editor.TextChanged += (_, _) => SaveSettingsOnEdit();
        BuildOverlay.Visibility = Visibility.Visible; RefreshUpgradeViews(); _populatingEditor = false;
        BuildError.Text = "Changes save automatically. Close when finished."; _rankEditor.Focus();
    }
    private static IEnumerable<Choice> GoalChoices() => new[] {
        new Choice("power", "Configured power contribution"), new Choice("attack", "Hero ATK total"), new Choice("health", "Hero HP total"),
        new Choice("defense", "Hero DEF total"), new Choice("direct", "Experimental direct-output potential") };
    private void DrawRankProgress(UpgradeStage? stage)
    {
        _starPreview.Children.Clear();
        _starSliderLabel.Text = StarProgress.Label(stage);
        _starPreview.ToolTip = "Five star slots: purple first, then gold replaces purple. Sectors show configured steps, not a fraction of fragment cost. Unknown rank is not zero stars.";
        BitmapImage Sprite(string name) => new(new Uri($"pack://application:,,,/TilesSurviveHeroPlanner;component/Images/{name}.png"));
        foreach (var slot in StarProgress.Slots(stage))
        {
            var grid = new Grid { Width = 36, Height = 36, Margin = new Thickness(0, 0, 4, 0), Opacity = stage is null ? .35 : 1 };
            grid.Children.Add(new Image { Source = Sprite(slot.BaseSprite) });
            if (slot.ProgressSprite is string progress)
            {
                var image = new Image { Source = Sprite(progress) };
                var points = new List<Point> { new(18, 18) };
                for (int i = 0; i <= slot.Steps * 12; i++)
                { double angle = (-90 - i * 5) * Math.PI / 180; points.Add(new(18 + 32 * Math.Cos(angle), 18 + 32 * Math.Sin(angle))); }
                var figure = new PathFigure { StartPoint = points[0], IsClosed = true };
                figure.Segments.Add(new PolyLineSegment(points.Skip(1), true)); image.Clip = new PathGeometry([figure]);
                grid.Children.Add(image);
            }
            _starPreview.Children.Add(grid);
        }
    }
    private const string UpgradeCaveats = "Ranks raise skill caps, not free skill levels. XP assumes zero progress toward the next level; check building gates in-game. Costs compare only the same resource ID; shard conversion is not assumed. Power/stat contributions are not measured combat strength. Direct-output mode is low-confidence (assumed affine scaling and millisecond cooldowns); animation hit counts, mitigation, targeting, healing, conditional buffs/debuffs, control and summons are not simulated. Equal returns are ties, not a hero preference.";
    private bool ReadSettings()
    {
        if (!int.TryParse(_secondsEditor.Text, out int seconds) || seconds is < 1 or > 300) { BuildError.Text = "Window must be a whole number from 1 to 300."; return false; }
        var inventory = new Dictionary<string, double>(_upgradeSettings.Inventory);
        foreach (var (id, input) in _budgetEditors)
        {
            if (string.IsNullOrWhiteSpace(input.Text)) { inventory.Remove(id); continue; }
            if (!double.TryParse(input.Text, NumberStyles.Number, CultureInfo.InvariantCulture, out double balance) || !double.IsFinite(balance) || balance is < 0 or > 1e12)
            { BuildError.Text = $"Enter a valid non-negative balance for {_upgradeData.Items.GetValueOrDefault(id) ?? id}, or leave blank."; return false; }
            inventory[id] = balance;
        }
        _upgradeSettings = new() { Goal = ((Choice)_goalEditor.SelectedItem).Id!, Seconds = seconds, Inventory = inventory, OnlyAffordable = _affordableEditor.IsChecked == true, TargetedPool = (_targetedPoolEditor.SelectedItem as Choice)?.Id };
        BuildError.Text = ""; return true;
    }
    private bool ReadBuild(out HeroBuild build)
    {
        build = new() { Stage = (_stageEditor.SelectedItem as Choice)?.Id };
        if ((_rankEditor.SelectedItem as Choice)?.Id is not null && build.Stage is null)
        { BuildError.Text = "Choose a step for this rank. Your previous data is unchanged."; return false; }
        bool Number(string text, string label, out int? n)
        {
            n = null; if (string.IsNullOrWhiteSpace(text)) return true;
            if (int.TryParse(text, out int value) && value is >= 0 and <= 1000) { n = value; return true; }
            BuildError.Text = $"{label}: enter a whole number from 0 to 1000, or leave blank."; return false;
        }
        if (!Number(_levelEditor.Text, "Hero level", out int? level)) return false; build.Level = level;
        var heroData = _upgradeData.Heroes[_editingHero!.AssetSlug];
        string? selectedStageId = build.Stage;
        var selectedStage = heroData.Stages.Find(s => s.Id == selectedStageId);
        if (level is int heroLevel && !heroData.Levels.Any(l => l.Level == heroLevel))
        { BuildError.Text = $"Hero level must match the game data (1–{heroData.Levels.Max(l => l.Level)}), or be blank."; return false; }
        foreach (var (id, input) in _skillEditors) { if (!Number(input.Text, "Skill level", out int? n)) return false; if (n is int v) build.Skills[id] = v; }
        foreach (var skill in heroData.Skills)
            if (build.Skills.TryGetValue(skill.Id, out int n) && (n > 0 && !skill.Levels.Any(l => l.Level == n) || selectedStage is not null && n > selectedStage.SkillCaps.ElementAtOrDefault(skill.Slot)))
            { BuildError.Text = $"{skill.Name}: level is above the current cap or absent from the game data."; return false; }
        if (_gearModeEditor.SelectedIndex == 1)
        {
            build.Gear = [];
            foreach (var (type, input) in _gearEditors.Values)
                if ((type.SelectedItem as Choice)?.Id is string id)
                {
                    if (!Number(input.Text, "Gear level", out int? n) || n is null) { BuildError.Text = "Selected gear needs a valid level."; return false; }
                    var gear = _upgradeData.Gear[id];
                    if (!gear.Levels.Any(l => l.Level == n) || level is int currentLevel && currentLevel < gear.HeroLevelRequired)
                    { BuildError.Text = "Gear level is invalid, or the hero level is too low for that gear."; return false; }
                    build.Gear.Add(new() { Id = id, Level = n.Value });
                }
        }
        // Partial records are allowed, but never receive a calculated return.
        if (build.Stage is not null && build.Level is not null && UpgradeModel.State(_editingHero!.AssetSlug, build, _upgradeData, _upgradeSettings.Seconds, out var error) is null)
        { BuildError.Text = error; return false; }
        return true;
    }
    private void SaveBuildOnEdit()
    {
        if (_populatingEditor || _editingHero is null) return;
        BuildError.Foreground = Brushes.Gold;
        if (!ReadBuild(out var build)) { BuildError.Text = "Not saved: " + BuildError.Text; return; }
        var slug = _editingHero.AssetSlug; var previous = _heroBuilds.GetValueOrDefault(slug);
        try
        {
            _heroBuilds[slug] = build; SaveProfile(); RefreshUpgradeViews();
            BuildError.Text = "Saved automatically."; BuildError.Foreground = Brushes.LightGreen;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            if (previous is null) _heroBuilds.Remove(slug); else _heroBuilds[slug] = previous;
            BuildError.Text = "Could not save: " + ex.Message;
        }
    }
    private void SaveSettingsOnEdit()
    {
        if (_populatingEditor || _editingHero is null) return;
        var previous = _upgradeSettings; BuildError.Foreground = Brushes.Gold;
        if (!ReadSettings()) { BuildError.Text = "Not saved: " + BuildError.Text; return; }
        try { SaveProfile(); RefreshUpgradeViews(); BuildError.Text = "Saved automatically."; BuildError.Foreground = Brushes.LightGreen; }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        { _upgradeSettings = previous; BuildError.Text = "Could not save: " + ex.Message; }
    }
    private void CloseBuild_Click(object sender, RoutedEventArgs e)
    {
        BuildOverlay.Visibility = Visibility.Collapsed; _editingHero = null;
        if (_focusBeforeOverlay is not null) Keyboard.Focus(_focusBeforeOverlay);
    }
    private void BuildOverlay_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape) { CloseBuild_Click(sender, e); e.Handled = true; }
    }
    private void RefreshUpgradeViews()
    {
        RefreshResourcePriority();
        if (ResourceRecommendation is not null) ResourceRecommendation.Text = "Choose five heroes, then use their small edit buttons to record current builds and compare data-driven next upgrades. No fixed hero order.";
        if (BuildOverlay.Visibility == Visibility.Visible)
        {
            _overlayResults.Children.Clear();
            if (_selected.Count != 5) { _overlayResults.Children.Add(Selectable("Select five heroes in Squad Builder first.")); return; }
            RenderUpgradeGroups(_overlayResults, UpgradeModel.Evaluate(_selected.Select(h => h.AssetSlug), _heroBuilds, _upgradeData, _upgradeSettings), "all", false);
            var draft = new StackPanel(); var heading = Selectable("", true); draft.Children.Add(heading);
            var cards = new StackPanel(); draft.Children.Add(cards); RenderTargetedDraft(cards, heading);
            _overlayResults.Children.Add(new Expander { Header = "Targeted Draft", Content = draft, Foreground = Brushes.White, Margin = new Thickness(0, 10, 0, 0) });
        }
    }
}
