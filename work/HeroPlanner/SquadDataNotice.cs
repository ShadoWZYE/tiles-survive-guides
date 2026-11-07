using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;
public partial class MainWindow
{
    private void RefreshSquadDataNotice()
    {
        SquadDataNotice.Children.Clear();
        var missing=_selected.Select(h=>new{Hero=h,Fields=EstimateModel.MissingBuild(h.AssetSlug,_heroBuilds.GetValueOrDefault(h.AssetSlug),_upgradeData)}).Where(x=>x.Fields.Count>0).ToList();
        var account=new List<string>();
        if(!_armyContext.Enabled)account.Add("Army bonuses disabled");
        if(_armyContext.Research.Count==0)account.Add("Research not recorded");
        if(_armyContext.BehemothSource=="configured" ? !_armyContext.BehemothBuilds.Values.Any(b=>b.Level>0||b.Star>0) : _armyContext.Behemoth.All(v=>v is null))account.Add("Behemoth bonuses not recorded");
        if(_comparisonBasis=="recorded"&&!_selected.Any(h=>_armyContext.Signature.ContainsKey(h.AssetSlug)))account.Add("Signature Gear not recorded (if owned)");
        if(missing.Count==0&&_selected.Count>0&&account.Count==0)return;
        var body=new StackPanel();
        string heading=_selected.Count==0?"Complete your squad data · select heroes first":missing.Count>0?$"Complete your squad data · {missing.Count} incomplete builds":"Check your account bonus data";
        SquadDataNotice.Children.Add(new Expander{Header=heading,Content=body,Foreground=Brushes.Gold});
        body.Children.Add(CopyText(_comparisonBasis=="recorded"?"Please fill in missing build values. Unknown level uses 1; unrecorded or locked upgrades add no bonus.":"This is a maximum-build comparison, not your current squad strength. Record your builds and select My builds for personal recommendations."));
        if(_selected.Count==0)body.Children.Add(CopyText("Select heroes, then record their level, exact rank/step, unlocked skills and equipped gear (or explicitly none)."));
        foreach(var item in missing){var button=new Button{Content="Fill missing data · "+item.Hero.Name,Tag=item.Hero,HorizontalContentAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,2,0,3),Padding=new Thickness(8,5,8,5)};button.Click+=(_,e)=>EditBuild_Click(button,e);body.Children.Add(button);body.Children.Add(CopyText(string.Join(", ",item.Fields)));}
        if(account.Count>0)body.Children.Add(CopyText(string.Join(" · ",account)));
        body.Children.Add(CopyText("Also record owned Signature Gear, Research and Behemoths in their sections. Leave unavailable or unowned bonuses blank; they are excluded."));
    }
}
