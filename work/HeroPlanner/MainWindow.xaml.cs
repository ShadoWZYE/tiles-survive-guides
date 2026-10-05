using System.Collections.ObjectModel;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow : Window
{
    private readonly List<Hero> _heroes = [];
    private readonly ObservableCollection<Hero> _selected = [];
    private readonly ObservableCollection<SquadResult> _topSquads = [];
    private readonly ObservableCollection<ReleaseScheduleItem> _releaseSchedule = [];
    private Hero? _activeHero;
    private Hero? _releaseHero;
    private Point _rosterDragStart;
    private double _rosterDragStartOffset;
    private bool _rosterDragPending;
    private bool _rosterDragging;
    private bool _syncingRosterScroll;
    private bool _loadingProfile;
    private static readonly DateTime AllianceServerOpenDate = new(2026, 9, 2);
    private static readonly string DefaultProfilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TilesSurviveHeroPlanner", "profile.json");

    private readonly string ProfilePath;

    public MainWindow() : this(DefaultProfilePath) { }

    // Isolated profile path also lets UI regression tests preserve the real user's save.
    private MainWindow(string profilePath)
    {
        ProfilePath = profilePath;
        InitializeComponent();
        LoadHeroes();
        LoadUpgradeData();
        LoadEstimates();
        LoadProfile();
        RefreshEstimates();
        SaveProfile();
        HeroRoster.ItemsSource = _heroes;
        SelectedSquad.ItemsSource = _selected;
        TopSquads.ItemsSource = _topSquads;
        ReleaseSchedule.ItemsSource = _releaseSchedule;
        SetActiveHero(_heroes[0]);
        InspectorTabs.SelectedIndex = 0;
        UpdateNavigationState(0);
        RebuildOptimizer();
        UpdateRecommendations();
        UpdateSquadPresentation();
    }

    private void LoadHeroes()
    {
        var streamInfo = Application.GetResourceStream(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Data/heroes.json"));
        if (streamInfo is null) throw new InvalidOperationException("Embedded hero data was not found.");
        using var stream = streamInfo.Stream;
        var heroes = JsonSerializer.Deserialize<List<Hero>>(stream) ?? [];
        _heroes.AddRange(heroes.OrderByDescending(hero => hero.CompositeIndex).ThenBy(hero => hero.Name));
    }

    private EstimateData _estimates = new();
    private void LoadEstimates()
    {
        var resource = Application.GetResourceStream(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Data/estimates.json"))!;
        using var reader = new StreamReader(resource.Stream); _estimates = EstimateData.Parse(reader.ReadToEnd());
        if (_heroes.Any(h => !_estimates.Heroes.ContainsKey(h.AssetSlug))) throw new InvalidDataException("Incomplete hero estimate coverage.");
    }
    private string? _lastEstimateBuilds;
    private bool RefreshEstimates()
    {
        string snapshot = JsonSerializer.Serialize(_heroBuilds);
        if (snapshot == _lastEstimateBuilds) return false;
        foreach (var hero in _heroes)
        {
            var result = EstimateModel.Evaluate(hero.AssetSlug, _heroBuilds.GetValueOrDefault(hero.AssetSlug), _upgradeData, _estimates);
            hero.Estimate = result; hero.OffenseIndex = result.Offense; hero.DurabilityIndex = result.Durability; hero.CompositeIndex = result.Score;
        }
        _heroes.Sort((a, b) => { int score = b.CompositeIndex.CompareTo(a.CompositeIndex); return score != 0 ? score : StringComparer.Ordinal.Compare(a.Name, b.Name); });
        HeroRoster.Items.Refresh();
        if (_activeHero is not null) { StatsPanel.DataContext = null; StatsPanel.DataContext = _activeHero; }
        _lastEstimateBuilds = snapshot;
        return true;
    }

    private void LoadProfile()
    {
        _loadingProfile = true;
        try
        {
            HashSet<string> owned = [];
            Dictionary<string, HeroProgress> progress = [];
            DateTime? serverOpenDate = AllianceServerOpenDate;
            if (File.Exists(ProfilePath))
            {
                string json = File.ReadAllText(ProfilePath);
                using JsonDocument document = JsonDocument.Parse(json);
                if (document.RootElement.ValueKind == JsonValueKind.Array)
                {
                    owned = JsonSerializer.Deserialize<HashSet<string>>(json) ?? [];
                }
                else
                {
                    var profile = JsonSerializer.Deserialize<PlannerProfile>(json) ?? new PlannerProfile();
                    owned = profile.OwnedHeroes;
                    progress = profile.HeroProgress ?? [];
                    _heroBuilds = (profile.HeroBuilds ?? []).Where(x => _heroes.Any(h => h.AssetSlug == x.Key) && x.Value is not null).ToDictionary();
                    _upgradeSettings = profile.UpgradeSettings ?? new();
                    _upgradeSettings.Clean();
                    serverOpenDate = profile.ServerOpenDate ?? AllianceServerOpenDate;
                }
            }
            foreach (var hero in _heroes)
            {
                hero.IsOwned = owned.Contains(hero.AssetSlug);
                if (progress.TryGetValue(hero.AssetSlug, out var entry) && entry is not null)
                    hero.Progress = new() { Current = HeroProgress.Clean(entry.Current), Target = HeroProgress.Clean(entry.Target) };
            }
            ServerOpenDate.SelectedDate = serverOpenDate;
        }
        catch (JsonException)
        {
            // A malformed hand-edited profile should not prevent the app from opening.
            ServerOpenDate.SelectedDate = AllianceServerOpenDate;
        }
        finally
        {
            _loadingProfile = false;
        }
    }

    private void SaveProfile()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(ProfilePath)!);
        var profile = new PlannerProfile
        {
            OwnedHeroes = _heroes.Where(hero => hero.IsOwned).Select(hero => hero.AssetSlug).ToHashSet(),
            HeroBuilds = _heroBuilds,
            UpgradeSettings = _upgradeSettings,
            HeroProgress = _heroes.Where(hero => hero.Progress.Current is not null || hero.Progress.Target is not null)
                .ToDictionary(hero => hero.AssetSlug, hero => hero.Progress),
            ServerOpenDate = ServerOpenDate.SelectedDate?.Date,
        };
        string pendingPath = ProfilePath + "." + Guid.NewGuid().ToString("N") + ".pending";
        try
        {
            File.WriteAllText(pendingPath, JsonSerializer.Serialize(profile, new JsonSerializerOptions { WriteIndented = true }));
            File.Move(pendingPath, ProfilePath, overwrite: true);
        }
        finally { if (File.Exists(pendingPath)) File.Delete(pendingPath); }
    }

    private PlannerMode CurrentMode => ((ComboBoxItem?)ModePicker.SelectedItem)?.Content?.ToString() switch
    {
        "Offense" => PlannerMode.Offense,
        "Survival" => PlannerMode.Survival,
        "PvE farming" => PlannerMode.Pve,
        _ => PlannerMode.Balanced,
    };

    private string CurrentAccess => ((ComboBoxItem?)AccessPicker.SelectedItem)?.Content?.ToString() ?? "All access";

    private bool MatchesAccess(Hero hero) => CurrentAccess switch
    {
        "Owned only" => hero.IsOwned,
        "F2P confirmed" => hero.AcquisitionClass == "f2p_confirmed",
        "F2P + events" => hero.AcquisitionClass is "f2p_confirmed" or "event_mixed",
        "IAP-linked" => hero.IapLinked,
        _ => true,
    };

    private void HeroCard_Click(object sender, RoutedEventArgs e)
    {
        if (BuildOverlay.Visibility == Visibility.Visible || (e.OriginalSource is not null && !ReferenceEquals(e.OriginalSource, sender))) return;
        if (sender is not Button { Tag: Hero hero }) return;
        SetActiveHero(hero);
        if (InspectorTabs.SelectedIndex == 4)
        {
            _releaseHero = hero;
            ReleaseEvidencePanel.DataContext = hero;
            ReleaseEvidencePanel.Visibility = Visibility.Visible;
            ReleaseSelectionHint.Visibility = Visibility.Collapsed;
            UpdateReleaseEstimate();
            return;
        }
        if (InspectorTabs.SelectedIndex == 3)
        {
            hero.IsOwned = !hero.IsOwned;
            HeroRoster.Items.Refresh(); SaveProfile(); RefreshOwnedState();
            return;
        }
        if (InspectorTabs.SelectedIndex != 0) return;
        if (_selected.Contains(hero)) _selected.Remove(hero);
        else if (_selected.Count < 5) _selected.Add(hero);
        NormalizeSelectedOrder();
        SelectionStatus.Text = $"{_selected.Count} / 5 selected";
        UpdateSquadPresentation();
    }

    private void HeroRosterScroll_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        _rosterDragStart = e.GetPosition(HeroRosterScroll);
        _rosterDragStartOffset = HeroRosterScroll.VerticalOffset;
        _rosterDragPending = true;
        _rosterDragging = false;
    }

    private void HeroRosterScroll_MouseMove(object sender, MouseEventArgs e)
    {
        if (!_rosterDragPending || e.LeftButton != MouseButtonState.Pressed) return;
        Point current = e.GetPosition(HeroRosterScroll);
        double delta = current.Y - _rosterDragStart.Y;
        if (!_rosterDragging && Math.Abs(delta) < SystemParameters.MinimumVerticalDragDistance) return;
        if (!_rosterDragging)
        {
            _rosterDragging = true;
            HeroRosterScroll.CaptureMouse();
            Mouse.OverrideCursor = Cursors.ScrollNS;
        }
        HeroRosterScroll.ScrollToVerticalOffset(_rosterDragStartOffset - delta);
        e.Handled = true;
    }

    private void HeroRosterScroll_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        bool wasDragging = _rosterDragging;
        EndRosterDrag();
        if (wasDragging) e.Handled = true;
    }

    private void HeroRosterScroll_LostMouseCapture(object sender, MouseEventArgs e)
    {
        // A Button losing capture when the ScrollViewer takes over also routes this event
        // through the ScrollViewer. That is the start of a drag, not its cancellation.
        if (!ReferenceEquals(e.OriginalSource, HeroRosterScroll)) return;
        _rosterDragPending = false;
        _rosterDragging = false;
        Mouse.OverrideCursor = null;
    }

    private void HeroRosterScroll_ScrollChanged(object sender, ScrollChangedEventArgs e)
    {
        if (HeroRosterBar is null || _syncingRosterScroll) return;
        _syncingRosterScroll = true;
        HeroRosterBar.Value = HeroRosterScroll.VerticalOffset;
        _syncingRosterScroll = false;
    }

    private void HeroRosterBar_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (HeroRosterScroll is null || _syncingRosterScroll) return;
        _syncingRosterScroll = true;
        HeroRosterScroll.ScrollToVerticalOffset(e.NewValue);
        _syncingRosterScroll = false;
    }

    private void EndRosterDrag()
    {
        _rosterDragPending = false;
        _rosterDragging = false;
        if (HeroRosterScroll.IsMouseCaptured) HeroRosterScroll.ReleaseMouseCapture();
        Mouse.OverrideCursor = null;
    }

    private void Navigation_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string tabText } || !int.TryParse(tabText, out int tabIndex)) return;
        InspectorTabs.SelectedIndex = tabIndex;
        UpdateNavigationState(tabIndex);
        RosterTitle.Text = tabIndex == 3 ? "My roster — select a hero to edit" : "Hero roster";
        if (tabIndex == 4)
        {
            _releaseHero = null;
            ReleaseEvidencePanel.DataContext = null;
            ReleaseEvidencePanel.Visibility = Visibility.Collapsed;
            ReleaseSelectionHint.Visibility = Visibility.Visible;
            UpdateReleaseSchedule(ServerOpenDate.SelectedDate);
        }
        HeroRoster.Items.Refresh();
    }

    private void UpdateNavigationState(int selectedIndex)
    {
        Button[] buttons = [SquadNav, StatsNav, SkillsNav, RosterNav, ReleaseNav];
        for (int index = 0; index < buttons.Length; index++)
        {
            bool selected = index == selectedIndex;
            buttons[index].Background = selected
                ? new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(22, 140, 135))
                : new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(42, 75, 120));
            buttons[index].BorderBrush = selected
                ? new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(61, 224, 212))
                : new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(69, 107, 158));
        }
    }

    private void SetActiveHero(Hero hero)
    {
        _activeHero = hero;
        StatsPanel.DataContext = hero;
        SkillsHeader.DataContext = hero;
        SkillsList.ItemsSource = hero.Skills.OrderBy(skill => skill.NormalAttack ? -1 : skill.Slot);
        StarHeroLabel.Text = $"{hero.Name} — optional star plan";
        ToggleActiveOwned.Content = hero.IsOwned ? "Remove owned check" : "Mark as owned";
        CurrentStars.Text = hero.Progress.Current?.ToString() ?? "";
        TargetStars.Text = hero.Progress.Target?.ToString() ?? "";
        StarSaveStatus.Text = "Leave blank if unknown. Whole stars only; input range is not the game's maximum.";
    }

    private void ToggleActiveOwned_Click(object sender, RoutedEventArgs e)
    {
        if (_activeHero is null) return;
        _activeHero.IsOwned = !_activeHero.IsOwned;
        ToggleActiveOwned.Content = _activeHero.IsOwned ? "Remove owned check" : "Mark as owned";
        SaveProfile();
        HeroRoster.Items.Refresh();
        RefreshOwnedState();
    }

    private void SaveStars_Click(object sender, RoutedEventArgs e)
    {
        if (_activeHero is null) return;
        bool TryStars(string text, out int? result)
        {
            result = null;
            if (string.IsNullOrWhiteSpace(text)) return true;
            if (int.TryParse(text, out int value) && HeroProgress.Clean(value) is not null) { result = value; return true; }
            return false;
        }
        if (!TryStars(CurrentStars.Text, out int? current) || !TryStars(TargetStars.Text, out int? target))
        {
            StarSaveStatus.Text = "Enter a whole number from 0 to 99, or leave blank. Nothing was changed.";
            return;
        }
        _activeHero.Progress = new() { Current = current, Target = target };
        SaveProfile();
        UpdateRecommendations();
        UpdateSquadPresentation();
        StarSaveStatus.Text = "Saved locally. Stars change the target queue, not simulated power.";
    }

    private void Clear_Click(object sender, RoutedEventArgs e)
    {
        _selected.Clear();
        SelectionStatus.Text = "0 / 5 selected";
        UpdateSquadPresentation();
    }

    private void Filter_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (HeroRoster is null) return;
        string faction = ((ComboBoxItem?)FactionFilter.SelectedItem)?.Content?.ToString() ?? "All factions";
        string role = ((ComboBoxItem?)RoleFilter.SelectedItem)?.Content?.ToString() ?? "All roles";
        string rarity = ((ComboBoxItem?)RarityFilter.SelectedItem)?.Content?.ToString() ?? "All rarities";
        HeroRoster.ItemsSource = _heroes.Where(hero =>
            (faction.StartsWith("All") || hero.Faction == faction) &&
            (role.StartsWith("All") || hero.Role == role) &&
            (rarity.StartsWith("All") || hero.Rarity == rarity)).ToList();
    }

    private void ModePicker_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (ReferenceEquals(sender, FormationModePicker))
        {
            if (ModePicker.SelectedIndex != FormationModePicker.SelectedIndex)
                ModePicker.SelectedIndex = FormationModePicker.SelectedIndex;
            return;
        }
        if (FormationModePicker is not null && FormationModePicker.SelectedIndex != ModePicker.SelectedIndex)
            FormationModePicker.SelectedIndex = ModePicker.SelectedIndex;
        NormalizeSelectedOrder();
        RebuildOptimizer();
        UpdateRecommendations();
        UpdateSquadPresentation();
    }

    private void OptimizerOption_Changed(object sender, RoutedEventArgs e)
    {
        RebuildOptimizer();
        UpdateRecommendations();
    }

    private void Optimize_Click(object sender, RoutedEventArgs e)
    {
        RebuildOptimizer();
        if (_topSquads.Count > 0) LoadSquad(_topSquads[0]);
    }

    private void TopSquads_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (TopSquads.SelectedItem is SquadResult squad) LoadSquad(squad);
    }

    private void LoadSquad(SquadResult squad)
    {
        _selected.Clear();
        foreach (var hero in squad.Heroes) _selected.Add(hero);
        NormalizeSelectedOrder();
        SelectionStatus.Text = "5 / 5 selected";
        UpdateSquadPresentation();
    }

    private void NormalizeSelectedOrder()
    {
        var ordered = OrderForFormation(_selected, CurrentMode).ToList();
        if (_selected.SequenceEqual(ordered)) return;
        _selected.Clear();
        foreach (var hero in ordered) _selected.Add(hero);
    }

    private void UpdateSquadPresentation()
    {
        if (OptimizerPanel is null || TopConfigurationsPanel is null || FormationGuidePanel is null) return;
        bool complete = _selected.Count == 5;
        OptimizerPanel.Visibility = complete ? Visibility.Collapsed : Visibility.Visible;
        TopConfigurationsPanel.Visibility = complete ? Visibility.Collapsed : Visibility.Visible;
        FormationGuidePanel.Visibility = complete ? Visibility.Visible : Visibility.Collapsed;
        if (!complete) return;

        var squad = OrderForFormation(_selected, CurrentMode).ToList();
        double baseScore = squad.Average(hero => ScoreHero(hero, CurrentMode));
        var synergy = EvaluateSynergy(squad, CurrentMode);
        var carries = FormationPriority.Carries(squad);
        var sustain = squad.Where(hero => hero.HasMechanic("Healing") || hero.HasMechanic("Shield") || hero.HasMechanic("Damage reduction")).ToList();
        var control = squad.Where(hero => hero.HasMechanic("Stun") || hero.HasMechanic("Slow")).ToList();
        var debuff = squad.Where(hero => hero.HasMechanic("ATK reduction") || hero.HasMechanic("DEF reduction")).ToList();

        FormationModeLabel.Text = $"{(CurrentMode == PlannerMode.Pve ? "PvE farming" : CurrentMode)} formation";
        FormationScoreLabel.Text = $"Modeled score {baseScore + synergy.Bonus:0.0}  •  {baseScore:0.0} base + {synergy.Bonus:0.0} synergy";
        FormationPositions.Text = string.Join("\n", squad.Select((hero, index) =>
            $"{index + 1}. {hero.Name} — {hero.FormationBand}; {PositionJob(hero, carries)}"));

        var functionParts = new List<string>
        {
            $"Modeled damage core: {string.Join(" and ", carries.Select(hero => hero.Name))}. This is not a measured DPS ranking."
        };
        if (debuff.Count > 0) functionParts.Add($"{string.Join("/", debuff.Select(hero => hero.Name).Take(2))} weakens targets before the main damage window.");
        if (control.Count > 0) functionParts.Add($"{string.Join("/", control.Select(hero => hero.Name).Take(2))} creates control windows.");
        if (sustain.Count > 0) functionParts.Add($"{string.Join("/", sustain.Select(hero => hero.Name).Take(2))} keeps the formation active through longer exchanges.");
        FormationFunction.Text = string.Join(" ", functionParts) + $" Modeled interaction: {synergy.Summary}.";

        var battleSteps = new List<string>();
        if (debuff.Count > 0) battleSteps.Add("Open on the same priority target so the debuffs benefit every follow-up hit");
        if (control.Count > 0) battleSteps.Add("commit burst while control is active instead of splitting damage");
        if (sustain.Count > 0) battleSteps.Add("keep the frontline together so healing and protection cover the carries");
        if (CurrentMode == PlannerMode.Pve && squad.Any(hero => hero.StaminaReductionPercent > 0))
            battleSteps.Add("use this squad for repeated PvE actions to benefit from the extracted Stamina reduction");
        FormationBattleGuide.Text = battleSteps.Count == 0
            ? "Focus one target at a time and protect the two highest-offense heroes; this squad has no strong extracted timing combo."
            : string.Join("; then ", battleSteps) + ".";

        RefreshUpgradeViews();

        var weaknesses = new List<string>();
        foreach (string role in new[] { "Melee", "Mid", "Range" })
            if (!squad.Any(hero => hero.Role == role)) weaknesses.Add($"no {role.ToLowerInvariant()} hero");
        if (sustain.Count == 0) weaknesses.Add("no extracted healing, shield, or damage-reduction layer");
        if (control.Count == 0) weaknesses.Add("no extracted stun or slow");
        if (!squad.Any(hero => hero.HasMechanic("DEF reduction"))) weaknesses.Add("no extracted defense break for burst damage");
        if (CurrentMode == PlannerMode.Pve && !squad.Any(hero => hero.StaminaReductionPercent > 0)) weaknesses.Add("no extracted Stamina economy effect");
        FormationWeaknesses.Text = weaknesses.Count == 0
            ? "No obvious structural gap in the extracted roles and mechanics. Exact cooldowns, targeting, gear, and live balance can still change performance."
            : "Main modeled gaps: " + string.Join("; ", weaknesses.Take(3)) + ".";
    }

    private static string PositionJob(Hero hero, IReadOnlyList<Hero> carries)
    {
        if (hero.Role == "Melee") return hero.HasMechanic("Shield") || hero.HasMechanic("Damage reduction") ? "absorb pressure and protect the line" : "hold the frontline";
        if (carries.Contains(hero)) return "priority damage carry";
        if (hero.HasMechanic("Healing")) return "sustain the squad";
        if (hero.HasMechanic("Stun") || hero.HasMechanic("Slow")) return "set up the damage window";
        if (hero.HasMechanic("ATK reduction") || hero.HasMechanic("DEF reduction")) return "apply team-wide enemy pressure";
        return "support the core rotation";
    }

    private string StarQueue(IEnumerable<Hero> squad)
    {
        var plan = FormationPriority.Rank(squad, CurrentMode).Select(x => x.Hero).ToList();
        var pending = plan.Where(h => h.Progress.Status == "pending").Select(h => $"{h.Name} {h.Progress.Current}★ → {h.Progress.Target}★").ToList();
        var unknown = plan.Where(h => h.Progress.Status == "unknown").Select(h => h.Name).ToList();
        var reached = plan.Where(h => h.Progress.Status == "reached").Select(h => h.Name).ToList();
        return string.Join(" ", new[] {
            pending.Count > 0 ? "Planned order: " + string.Join("; ", pending) + "." : "No pending star targets recorded.",
            unknown.Count > 0 ? "Not assessed (missing stars/target): " + string.Join(", ", unknown) + "." : "",
            reached.Count > 0 ? "Target reached: " + string.Join(", ", reached) + "." : "",
            "Set stars in My roster. Check the next skill unlock and shard cost in-game; stars do not rescale the modeled squad score. Reaching a star target does not finish gear or skills."
        }.Where(s => s.Length > 0));
    }

    private static IEnumerable<Hero> OrderForFormation(IEnumerable<Hero> heroes, PlannerMode mode) => heroes
        .OrderBy(hero => hero.Role switch { "Melee" => 0, "Mid" => 1, "Range" => 2, _ => 3 })
        .ThenByDescending(hero => hero.Role switch
        {
            "Melee" => hero.DurabilityIndex,
            "Range" => hero.OffenseIndex,
            _ => ScoreHero(hero, mode),
        })
        .ThenBy(hero => hero.Name);

    private void RebuildOptimizer()
    {
        if (TopSquads is null || RoleCoverage is null || ModePicker is null || AccessPicker is null) return;
        var pool = _heroes.Where(MatchesAccess).ToList();
        var results = FindTopSquads(pool, CurrentMode, RoleCoverage.IsChecked == true, 20);
        _topSquads.Clear();
        for (int i = 0; i < results.Count; i++)
        {
            var result = results[i];
            _topSquads.Add(new SquadResult
            {
                Heroes = result.Heroes,
                Score = result.Score,
                BaseScore = result.BaseScore,
                SynergyBonus = result.SynergyBonus,
                SynergySummary = result.SynergySummary,
                Label = $"#{i + 1}"
            });
        }
        TopConfigurationsStatus.Text = results.Count == 0
            ? CurrentAccess == "Owned only" ? "Mark at least five compatible owned heroes in ROSTER." : $"No valid five-hero squad in {CurrentAccess}."
            : $"{results.Count} highest-scoring configurations • {CurrentMode switch { PlannerMode.Pve => "PvE farming", _ => CurrentMode.ToString() }} • {CurrentAccess} • shown front-to-back";
    }

    private static List<SquadResult> FindTopSquads(IReadOnlyList<Hero> pool, PlannerMode mode, bool requireRoleCoverage, int limit)
    {
        var best = new PriorityQueue<SquadResult, double>();
        int count = pool.Count;
        if (count < 5 || limit <= 0) return [];
        for (int a = 0; a < count - 4; a++)
        for (int b = a + 1; b < count - 3; b++)
        for (int c = b + 1; c < count - 2; c++)
        for (int d = c + 1; d < count - 1; d++)
        for (int e = d + 1; e < count; e++)
        {
            Hero[] squad = [pool[a], pool[b], pool[c], pool[d], pool[e]];
            if (requireRoleCoverage && squad.Select(hero => hero.Role).Distinct().Count() < 3) continue;
            double baseScore = squad.Average(hero => ScoreHero(hero, mode));
            double synergyBonus = EvaluateSynergy(squad, mode, false).Bonus;
            double score = baseScore + synergyBonus;
            bool shouldKeep = best.Count < limit ||
                (best.TryPeek(out _, out double lowestScore) && score > lowestScore);
            if (!shouldKeep) continue;
            var result = new SquadResult { Heroes = squad, BaseScore = baseScore, SynergyBonus = synergyBonus, Score = score, Label = "" };
            if (best.Count < limit)
            {
                best.Enqueue(result, result.Score);
            }
            else
            {
                best.Dequeue();
                best.Enqueue(result, result.Score);
            }
        }
        return best.UnorderedItems.Select(item => item.Element)
            .Select(result => new SquadResult
            {
                Heroes = OrderForFormation(result.Heroes, mode).ToArray(),
                BaseScore = result.BaseScore,
                SynergyBonus = result.SynergyBonus,
                SynergySummary = EvaluateSynergy(result.Heroes, mode).Summary,
                Score = result.Score,
                Label = "",
            })
            .OrderByDescending(result => result.Score).ThenBy(result => result.Names).ToList();
    }

    private static double ScoreHero(Hero hero, PlannerMode mode) => mode switch
    {
        PlannerMode.Offense => hero.OffenseIndex * 0.75 + hero.CompositeIndex * 0.25,
        PlannerMode.Survival => hero.DurabilityIndex * 0.75 + hero.CompositeIndex * 0.25,
        PlannerMode.Pve => hero.OffenseIndex * 0.45 + hero.DurabilityIndex * 0.30 + hero.CompositeIndex * 0.25
            + Math.Min(40, hero.StaminaReductionPercent * 1.30),
        _ => hero.CompositeIndex,
    };

    private static (double Bonus, string Summary) EvaluateSynergy(IReadOnlyList<Hero> squad, PlannerMode mode, bool includeSummary = true)
    {
        var interactions = includeSummary ? new List<string>() : null;
        double bonus = 0;
        HeroMechanic combined = HeroMechanic.None;
        foreach (var hero in squad) combined |= hero.MechanicFlags;
        bool Has(HeroMechanic mechanic) => (combined & mechanic) != 0;
        string Providers(string mechanic) => string.Join("/", squad
            .Where(hero => hero.HasMechanic(mechanic)).Select(hero => hero.Name).Take(2));
        string Carries() => string.Join("/", squad.OrderByDescending(hero => hero.OffenseIndex)
            .Take(2).Select(hero => hero.Name));

        if (Has(HeroMechanic.DefenseReduction))
        {
            bonus += mode switch { PlannerMode.Offense => 1.2, PlannerMode.Survival => 0.8, PlannerMode.Pve => 1.1, _ => 1.0 };
            if (includeSummary) interactions!.Add($"{Providers("DEF reduction")} DEF break → {Carries()}");
        }

        bool sustain = Has(HeroMechanic.Healing) || Has(HeroMechanic.Shield) || Has(HeroMechanic.DamageReduction);
        if (Has(HeroMechanic.AttackReduction) && sustain)
        {
            bonus += mode switch { PlannerMode.Survival => 1.2, PlannerMode.Offense => 0.7, PlannerMode.Pve => 1.0, _ => 0.9 };
            if (includeSummary) interactions!.Add($"{Providers("ATK reduction")} ATK down + sustain");
        }

        if (Has(HeroMechanic.Healing) && (Has(HeroMechanic.Shield) || Has(HeroMechanic.DamageReduction)))
        {
            bonus += mode switch { PlannerMode.Survival => 1.5, PlannerMode.Offense => 0.8, PlannerMode.Pve => 1.2, _ => 1.1 };
            if (includeSummary)
            {
                string protection = Has(HeroMechanic.Shield) ? Providers("Shield") : Providers("Damage reduction");
                interactions!.Add($"{Providers("Healing")} healing + {protection} protection");
            }
        }

        bool control = Has(HeroMechanic.Stun) || Has(HeroMechanic.Slow);
        if (control)
        {
            int controllerCount = squad.Count(hero => (hero.MechanicFlags & (HeroMechanic.Stun | HeroMechanic.Slow)) != 0);
            bonus += mode switch { PlannerMode.Offense => 0.8, PlannerMode.Survival => 0.8, PlannerMode.Pve => 0.6, _ => 0.7 };
            bonus += Math.Min(0.3, Math.Max(0, controllerCount - 1) * 0.15);
            if (includeSummary)
            {
                string controllers = string.Join("/", squad.Where(hero =>
                    hero.HasMechanic("Stun") || hero.HasMechanic("Slow")).Select(hero => hero.Name).Take(2));
                interactions!.Add($"{controllers} control → {Carries()} damage window");
            }
        }

        if (Has(HeroMechanic.DamageBoost) || Has(HeroMechanic.CriticalEffect))
        {
            int supporterCount = squad.Count(hero => (hero.MechanicFlags & (HeroMechanic.DamageBoost | HeroMechanic.CriticalEffect)) != 0);
            bonus += mode switch { PlannerMode.Offense => 1.2, PlannerMode.Survival => 0.6, PlannerMode.Pve => 1.0, _ => 0.9 };
            bonus += Math.Min(0.3, Math.Max(0, supporterCount - 1) * 0.15);
            if (includeSummary)
            {
                string supporters = string.Join("/", squad.Where(hero =>
                    hero.HasMechanic("Damage boost") || hero.HasMechanic("Critical effect")).Select(hero => hero.Name).Take(2));
                interactions!.Add($"{supporters} offense support → {Carries()}");
            }
        }

        if (Has(HeroMechanic.Summon) && (control || Has(HeroMechanic.DefenseReduction) || Has(HeroMechanic.DamageBoost) || Has(HeroMechanic.CriticalEffect)))
        {
            bonus += 0.35;
            if (includeSummary) interactions!.Add($"{Providers("Summon")} summon + team utility");
        }

        if (includeSummary && mode == PlannerMode.Pve)
        {
            var staminaHero = squad.OrderByDescending(hero => hero.StaminaReductionPercent).FirstOrDefault();
            if (staminaHero?.StaminaReductionPercent > 0)
                interactions?.Insert(0, $"{staminaHero.Name} −{staminaHero.StaminaReductionPercent:0.#}% Stamina cost");
        }

        double capped = Math.Min(6.0, bonus);
        if (!includeSummary) return (capped, "");
        string summary = interactions!.Count == 0
            ? "No modeled cross-skill pairing"
            : string.Join(" • ", interactions.Take(3)) + (interactions.Count > 3 ? $" • +{interactions.Count - 3} more" : "");
        return (capped, summary);
    }

    private void Ownership_Changed(object sender, RoutedEventArgs e)
    {
        e.Handled = true;
        if (_loadingProfile || sender is not CheckBox { IsLoaded: true, DataContext: Hero hero } check) return;
        hero.IsOwned = check.IsChecked == true;
        SaveProfile();
        RefreshOwnedState();
    }

    private void MarkAllOwned_Click(object sender, RoutedEventArgs e) => SetAllOwned(true);
    private void ClearOwned_Click(object sender, RoutedEventArgs e) => SetAllOwned(false);

    private void SetAllOwned(bool owned)
    {
        foreach (var hero in _heroes) hero.IsOwned = owned;
        HeroRoster.Items.Refresh();
        SaveProfile();
        RefreshOwnedState();
    }

    private void RefreshOwnedState()
    {
        if (_activeHero is not null && ToggleActiveOwned is not null)
            ToggleActiveOwned.Content = _activeHero.IsOwned ? "Remove owned check" : "Mark as owned";
        OwnedCount.Text = $"{_heroes.Count(hero => hero.IsOwned)} / {_heroes.Count} marked as owned";
        RebuildOptimizer();
        UpdateRecommendations();
    }

    private void UpdateRecommendations()
    {
        if (UnlockRecommendation is null || ResourceRecommendation is null) return;
        var owned = _heroes.Where(hero => hero.IsOwned).ToList();
        var allUnowned = _heroes.Where(hero => !hero.IsOwned).ToList();
        var unowned = CurrentAccess switch
        {
            "F2P confirmed" => allUnowned.Where(hero => hero.AcquisitionClass == "f2p_confirmed").ToList(),
            "F2P + events" => allUnowned.Where(hero => hero.AcquisitionClass is "f2p_confirmed" or "event_mixed").ToList(),
            "IAP-linked" => allUnowned.Where(hero => hero.IapLinked).ToList(),
            _ => allUnowned,
        };
        OwnedCount.Text = $"{owned.Count} / {_heroes.Count} marked as owned";
        if (owned.Count < 5)
        {
            int needed = 5 - owned.Count;
            var targets = unowned.OrderByDescending(hero => ScoreHero(hero, CurrentMode)).Take(Math.Max(needed, 3)).Select(hero => hero.Name);
            UnlockRecommendation.Text = $"Mark your remaining heroes. Strongest current candidates are: {string.Join(", ", targets)}.";
            ResourceRecommendation.Text = "Use the small edit buttons below the owned checkboxes to record builds. Select a five-hero formation for upgrade comparisons.";
            return;
        }

        bool coverage = RoleCoverage?.IsChecked == true;
        var current = FindTopSquads(owned, CurrentMode, coverage, 1).FirstOrDefault()
            ?? FindTopSquads(owned, CurrentMode, false, 1).First();
        var upgrades = unowned.Select(candidate =>
        {
            var candidatePool = owned.Append(candidate).ToList();
            var squad = FindTopSquads(candidatePool, CurrentMode, coverage, 1).FirstOrDefault()
                ?? FindTopSquads(candidatePool, CurrentMode, false, 1).First();
            return (candidate, squad, gain: squad.Score - current.Score);
        }).OrderByDescending(item => item.gain).ThenByDescending(item => item.squad.Score).Take(3).ToList();

        UnlockRecommendation.Text = upgrades.Count == 0
            ? "You own the complete extracted roster."
            : "Best modeled next targets: " + string.Join("; ", upgrades.Select(item =>
                $"{item.candidate.Name} ({(item.gain > 0 ? "+" : "")}{item.gain:0.0} squad points)")) + ".";
        ResourceRecommendation.Text = "Use the small edit buttons below the owned checkboxes for next-step cost and stat comparisons. Unlock suggestions here remain max-configuration heuristics.";
    }

    private void ServerOpenDate_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (!_loadingProfile) SaveProfile();
        UpdateReleaseEstimate();
    }

    private void UpdateReleaseEstimate()
    {
        if (ReleaseEstimate is null || ServerOpenDate is null) return;
        UpdateReleaseSchedule(ServerOpenDate.SelectedDate);
        if (_releaseHero is null) return;
        if (_releaseHero.ReleaseWeekMin is null)
        {
            ReleaseEstimate.Text = "No server-age release rule exists for this hero in the client.";
            return;
        }
        if (ServerOpenDate.SelectedDate is not DateTime openDate)
        {
            ReleaseEstimate.Text = "Enter a server opening date to calculate an estimate.";
            return;
        }
        int firstWeek = _releaseHero.ReleaseWeekMin.Value;
        int lastWeek = _releaseHero.ReleaseWeekMax ?? firstWeek;
        DateTime start = openDate.Date.AddDays((firstWeek - 1) * 7);
        DateTime end = openDate.Date.AddDays(lastWeek * 7 - 1);
        ReleaseEstimate.Text = start == end ? start.ToString("d MMMM yyyy") : $"{start:d MMM yyyy} – {end:d MMM yyyy}";
    }

    private void UpdateReleaseSchedule(DateTime? selectedOpenDate)
    {
        if (NextReleaseTitle is null || NextReleaseDates is null || NextReleaseCountdown is null || ReleaseSchedule is null) return;
        _releaseSchedule.Clear();
        if (selectedOpenDate is not DateTime openDate)
        {
            NextReleaseTitle.Text = "Enter your server opening date";
            NextReleaseDates.Text = "The next configured hero window will appear here.";
            NextReleaseCountdown.Text = "The timeline updates automatically.";
            return;
        }

        DateTime today = DateTime.Today;
        var windows = _heroes.Where(hero => hero.ReleaseWeekMin is not null)
            .Select(hero =>
            {
                int firstWeek = hero.ReleaseWeekMin!.Value;
                int lastWeek = hero.ReleaseWeekMax ?? firstWeek;
                return new
                {
                    Hero = hero,
                    FirstWeek = firstWeek,
                    LastWeek = lastWeek,
                    Start = openDate.Date.AddDays((firstWeek - 1) * 7),
                    End = openDate.Date.AddDays(lastWeek * 7 - 1),
                };
            })
            .OrderBy(item => item.Start)
            .ToList();

        var upcoming = windows.Where(item => item.End >= today).ToList();
        var current = upcoming.FirstOrDefault(item => item.Start <= today && item.End >= today);
        var next = upcoming.FirstOrDefault(item => item.Start > today);
        if (next is null && current is null)
        {
            NextReleaseTitle.Text = "No later configured releases";
            NextReleaseDates.Text = "All extracted server-age windows are already in the past.";
            NextReleaseCountdown.Text = "A future client update may add more.";
            return;
        }

        var headline = next ?? current!;
        NextReleaseTitle.Text = next is not null ? $"NEXT: {next.Hero.Name}" : $"FINAL CONFIGURED WINDOW: {headline.Hero.Name}";
        NextReleaseDates.Text = $"{headline.Start:d MMM yyyy} – {headline.End:d MMM yyyy}  •  server weeks {headline.FirstWeek}–{headline.LastWeek}";
        NextReleaseCountdown.Text = next is not null
            ? $"Starts in {(next.Start - today).Days} days." + (current is null ? "" : $" Current window: {current.Hero.Name} through {current.End:d MMM}.")
            : $"Active now and ends in {Math.Max(0, (headline.End - today).Days)} days; no later client window is configured.";

        foreach (var item in upcoming.Take(12))
        {
            bool isCurrent = ReferenceEquals(item, current);
            bool isNext = ReferenceEquals(item, next);
            string relative = item.Start <= today
                ? "Active configured window"
                : $"In {(item.Start - today).Days} days";
            _releaseSchedule.Add(new ReleaseScheduleItem
            {
                Marker = isCurrent ? "NOW" : isNext ? "NEXT" : $"W{item.FirstWeek}",
                HeroName = item.Hero.Name,
                WeekLabel = $"Weeks {item.FirstWeek}–{item.LastWeek}",
                DateLabel = $"{item.Start:d MMM} – {item.End:d MMM yyyy}",
                RelativeLabel = relative,
            });
        }
    }
}
