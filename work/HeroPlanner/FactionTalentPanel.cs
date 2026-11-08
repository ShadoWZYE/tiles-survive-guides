using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;
public partial class MainWindow
{
 private void RenderFactionTalents()
 {
  var panel=FactionTalentsPanel;panel.Children.Clear();
  panel.Children.Add(CopyText("Faction Star Talents",true));
  panel.Children.Add(CopyText("Record purchased node levels and TOTAL Star Points from the game (not the remaining Available amount). Each faction has its own point pool. Unspent points grant no stats. All-hero bonuses affect every faction and every army once."));
  panel.Children.Add(CopyText("Complete stars on eligible owned blue/purple/orange heroes supply points; partial stars and X heroes do not. Use the in-game total as authority; the planner does not assume an incomplete roster is your whole account."));
  var current=CopyContext();var enabled=new CheckBox{Content="Include recorded army bonuses",IsChecked=current.Enabled,Foreground=Brushes.White,Margin=new Thickness(0,8,0,8)};panel.Children.Add(enabled);
  var summary=CopyText("");panel.Children.Add(summary);
  var recommendations=CopyText("");panel.Children.Add(recommendations);
  var budgets=new Dictionary<string,TextBox>();var pickers=new Dictionary<string,ComboBox>();
  var grid=new System.Windows.Controls.Primitives.UniformGrid{Columns=3};panel.Children.Add(grid);
  foreach(var (branch,b) in _armyContextData.FactionTalents){
   var body=new StackPanel{Margin=new Thickness(8)};grid.Children.Add(body);body.Children.Add(CopyText(b.Name,true));
   var budget=new TextBox{Width=120,HorizontalAlignment=HorizontalAlignment.Left,Text=current.FactionPoints.TryGetValue(branch,out int n)?n.ToString():"",ToolTip="Total earned Star Points; blank = unknown"};budgets[branch]=budget;Field(body,"Total Star Points",budget);
   System.Windows.Automation.AutomationProperties.SetName(budget,"Faction total points "+branch);
   foreach(var (serial,node) in b.Nodes){string key=branch+":"+serial;var card=new StackPanel{Margin=new Thickness(0,10,0,4)};body.Children.Add(card);
    var title=new DockPanel();card.Children.Add(title);
    if(!string.IsNullOrEmpty(node.IconAsset))title.Children.Add(ContextIcon(node.IconAsset,36));title.Children.Add(CopyText(serial+" · "+node.Name,true));
    var picker=new ComboBox{MinWidth=150};picker.Items.Add(new ComboBoxItem{Content="Unrecorded / 0",Tag=0});picker.SelectedIndex=0;
    foreach(var row in node.Levels){var item=new ComboBoxItem{Content=$"Level {row.Level} · {row.Cost} points to upgrade",Tag=row.Level};picker.Items.Add(item);if(current.FactionTalents.GetValueOrDefault(key)==row.Level)picker.SelectedItem=item;}card.Children.Add(picker);pickers[key]=picker;
    System.Windows.Automation.AutomationProperties.SetName(picker,"Faction talent "+key);
    var description=CopyText("");card.Children.Add(description);
    void Describe(){int level=(int)((ComboBoxItem)picker.SelectedItem).Tag;var row=node.Levels.First(r=>r.Level==Math.Max(1,level));var required=node.Levels[0].Requires.Select(id=>b.Nodes.Values.SelectMany(v=>v.Levels.Select(r=>(Node:v,Row:r))).First(x=>x.Row.Id==id)).Select(x=>x.Node.Name+" Lv "+x.Row.Level);description.Text=(required.Any()?"Requires "+string.Join(" + ",required)+"\n":"")+row.Description+(level==0?" (level 1 preview)":"")+"\n"+(row.Effects.Count>0?"All-hero flat stats included when enabled.":"Effect excluded from hero score; troop/conditional runtime not verified.");}
    picker.SelectionChanged+=(_,_)=>{Describe();Preview();};Describe();
   }
   budget.TextChanged+=(_,_)=>Preview();
  }
  ArmyContextSettings Read(){var s=CopyContext();s.Enabled=enabled.IsChecked==true;s.FactionTalents=pickers.Where(p=>(int)((ComboBoxItem)p.Value.SelectedItem).Tag>0).ToDictionary(p=>p.Key,p=>(int)((ComboBoxItem)p.Value.SelectedItem).Tag);s.FactionPoints=[];foreach(var (key,input) in budgets)if(int.TryParse(input.Text,out int value)&&value>=0&&value<=100000)s.FactionPoints[key]=value;return s;}
  void Preview(){if(budgets.Count!=_armyContextData.FactionTalents.Count||pickers.Count!=_armyContextData.FactionTalents.Sum(b=>b.Value.Nodes.Count))return;var s=Read();var errors=_armyContextData.FactionTalents.Keys.SelectMany(b=>FactionTalentModel.Errors(s,_armyContextData,b)).ToList();
   summary.Text=string.Join(" · ",_armyContextData.FactionTalents.Select(b=>$"{b.Value.Name}: spent {FactionTalentModel.Spent(b.Key,s,_armyContextData)} / {(s.FactionPoints.TryGetValue(b.Key,out int total)?total.ToString():"unknown total")}"));
   if(errors.Count>0){recommendations.Text=string.Join("\n",errors);return;}
   if(_selected.Count==0){recommendations.Text="Select your squad to rank affordable upgrades by mean hero-score gain per Star Point.";return;}
   if(_comparisonBasis=="flat"){recommendations.Text="Max heroes (no gear) excludes account context. Switch to My builds or Equal builds for talent recommendations.";return;}
   double Score(ArmyContextSettings candidate){var full=Read();full.Enabled=true;full.FactionTalents=candidate.FactionTalents;return _selected.Average(h=>EstimateModel.Compare(h.AssetSlug,_heroBuilds.GetValueOrDefault(h.AssetSlug),_upgradeData,_estimates,_comparisonBasis,_battleSeconds,ArmyContextModel.Resolve(h.AssetSlug,full,_armyContextData,_comparisonBasis).Flat).Score);}
   var choices=FactionTalentModel.Recommend(s,_armyContextData,Score);recommendations.Text="Next affordable upgrades within each faction · selected squad · mean hero-score gain per point (not battle damage):\n"+string.Join("\n",choices.Select(c=>c.Modeled?$"{c.Name} → Lv {c.Level}: +{c.Gain:F2} score / {c.Cost} points = {c.GainPerPoint:F2}/point":$"{c.Name} → Lv {c.Level}: {c.Cost} points · effect not scored"));if(choices.Count==0)recommendations.Text+="Enter each faction's total points; no affordable legal upgrade is currently known.";
  }
  var status=CopyText("");var save=new Button{Content="Save faction talents",HorizontalAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,12,0,6),Padding=new Thickness(14,8,14,8)};panel.Children.Add(save);panel.Children.Add(status);
  save.Click+=(_,_)=>{var next=Read();foreach(var input in budgets.Values)if(!string.IsNullOrWhiteSpace(input.Text)&&(!int.TryParse(input.Text,out int n)||n<0||n>100000)){status.Text="Enter a non-negative whole point total, or leave blank. Nothing saved.";return;}var errors=_armyContextData.FactionTalents.Keys.SelectMany(b=>FactionTalentModel.Errors(next,_armyContextData,b)).ToList();if(errors.Count>0){status.Text=string.Join("\n",errors)+". Nothing saved.";return;}SaveContextSelection(next,status);};
  enabled.Click+=(_,_)=>Preview();Preview();
 }
}
