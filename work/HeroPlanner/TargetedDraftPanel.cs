using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow
{
    private void RenderTargetedDraft(Panel target, TextBox summary)
    {
        target.Children.Clear();
        summary.Text = "TARGETED DRAFT · choose a five-hero formation first";
        if (_selected.Count != 5) return;
        var pool = _upgradeData.TargetedDraft?.Pools.Find(p => p.Id == _upgradeSettings.TargetedPool);
        if (pool is null)
        {
            summary.Text = "TARGETED DRAFT · choose your in-game pool";
            target.Children.Add(Selectable("Open any hero's build editor → Upgrade comparison → Targeted Draft pool."));
            return;
        }
        var result = UpgradeModel.EvaluateTargeted(_selected.Select(h => h.AssetSlug), _heroBuilds, _upgradeData, _upgradeSettings, pool);
        var first = result.Candidates.FirstOrDefault(c => c.Efficiency > 0);
        bool provisional = result.Candidates.Any(c => c.Balance is null);
        summary.Text = first is null ? "TARGETED DRAFT · no positive, level-eligible target to rank" :
            $"TARGETED DRAFT · {(provisional ? "Provisional target" : "Suggested target")}: {first.Name}";
        target.Children.Add(Selectable($"Compared by {_upgradeSettings.Goal} milestone gain per missing fragment, not total hero strength."));
        if (provisional) target.Children.Add(Selectable("Some fragment balances are unknown. Enter them in the build editor for a more accurate target.", color: Brushes.Gold));
        var affordable = result.Candidates.Where(c => c.Remaining == 0 && c.Blocked is null).ToList();
        if (affordable.Count > 0) target.Children.Add(Selectable("Use existing fragments first: " + string.Join(", ", affordable.Select(c => c.Name)) + ". Update your build after upgrading.", color: Brushes.LightGreen));
        foreach (var c in result.Candidates)
        {
            var card = new StackPanel();
            target.Children.Add(new Border { Child = card, Background = new SolidColorBrush(Color.FromRgb(20, 39, 65)),
                CornerRadius = new CornerRadius(8), Padding = new Thickness(12), Margin = new Thickness(0, 6, 0, 3) });
            card.Children.Add(Selectable(c.Name + (c == first ? " · recommended target" : "") + (c.Blocked is null ? "" : " · locked"), true));
            card.Children.Add(Selectable($"Formation gain  +{c.Gain:0.####}%" +
                (c.Efficiency is double e ? $"\nPer 100 missing fragments  +{e:0.####}%" : "\nFragment efficiency unavailable"), color: Brushes.LightGreen));
            card.Children.Add(Selectable($"Goal: complete rank {c.Rank} · step {c.Step}/6\nFragments to reach goal: {c.Cost:0.##}\n" +
                (c.Balance is double balance ? $"Held: {balance:0.##}  ·  Still needed: {c.Remaining:0.##}" : "Held: unknown  ·  Full remaining cost used for comparison")));
            if (c.Blocked is not null) card.Children.Add(Selectable(c.Blocked, color: Brushes.Gold));
            card.Children.Add(new Expander { Header = "Milestone skill caps", Foreground = Brushes.White,
                Content = Selectable($"Caps: {string.Join(" / ", c.SkillCaps)}\nSkill upgrades still cost books. Higher caps do not grant free skill levels.") });
        }
        if (result.Missing.Count > 0) target.Children.Add(Selectable("Missing build data\n" + string.Join("\n", result.Missing), color: Brushes.Gold));
        var outside = pool.Choices.Where(c => _selected.All(h => h.AssetSlug != c.Slug))
            .Select(c => _upgradeData.Heroes.GetValueOrDefault(c.Slug)?.Name ?? c.HeroInternal).ToList();
        if (outside.Count > 0) target.Children.Add(new Expander { Header = "Pool heroes outside this formation", Foreground = Brushes.White,
            Content = Selectable(string.Join(", ", outside) + "\nReplacement / unlock value is not modeled.") });
        var notes = new StackPanel();
        notes.Children.Add(Selectable("POOL & ACCESS", true));
        notes.Children.Add(Selectable($"Pool: {pool.Id}\nSingle draw: {pool.SingleCost} voucher(s)\nConfigured unlock level: {pool.UnlockLevel} · check live access"));
        notes.Children.Add(Selectable("DISPLAYED SELECTED-TARGET RATES", true));
        notes.Children.Add(Selectable($"Hero: {pool.SelectedHeroChance}\nFragments: {pool.SelectedShardChance}\nBonus hero cards: {pool.SelectedBonusChance}\nThese rates are not fragment yields or guarantees per voucher."));
        notes.Children.Add(Selectable("WHAT THIS COMPARISON DOES NOT INCLUDE", true));
        notes.Children.Add(Selectable("• Expected combat return per voucher\n• Duplicate conversion or pity progress\n• Unlock / replacement value or utility skills\n\nEqual rates allow fragment-efficiency comparisons. Live availability may differ; building gates still apply."));
        target.Children.Add(new Expander { Header = "Pool rates, access & model limits", Content = notes, Foreground = Brushes.White, Margin = new Thickness(0, 10, 0, 0) });
    }
}
