using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
namespace TilesSurviveHeroPlanner;
public partial class MainWindow
{
 private ArmyContextData _armyContextData=new();
 private ArmyContextSettings _armyContext=new();
 private void LoadArmyContextData(){var resource=Application.GetResourceStream(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Data/army-context.json"))!;using var reader=new StreamReader(resource.Stream);_armyContextData=ArmyContextData.Parse(reader.ReadToEnd());}
 private void ArmyContext_Click(object sender,RoutedEventArgs e)
 {
  var current=ArmyContextModel.Clean(_armyContext,_armyContextData);
  var window=new Window{Title="Signature Gear, Behemoth & Research",Owner=this,Width=850,Height=760,MinWidth=560,MinHeight=480,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=new SolidColorBrush(Color.FromRgb(16,36,62)),Foreground=Brushes.White};
  var panel=new StackPanel{Margin=new Thickness(20)};window.Content=new ScrollViewer{Content=panel,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  void Note(string text,bool heading=false)=>panel.Children.Add(CopyText(text,heading));
  Note("Army stat context",true);Note("Optional stat-only context. Blank sources remain excluded / unknown. Flat max stats ignores this panel.");
  var enabled=new CheckBox{Content="Apply recorded stat context",IsChecked=current.Enabled,Foreground=Brushes.White,Margin=new Thickness(0,6,0,8)};panel.Children.Add(enabled);
  var scene=new ComboBox{Width=200,HorizontalAlignment=HorizontalAlignment.Left};foreach(var pair in new[]{("all","General / PvP"),("pve","PvE"),("gve","GVE")}){var item=new ComboBoxItem{Content=pair.Item2,Tag=pair.Item1};scene.Items.Add(item);if(pair.Item1==current.Scene)scene.SelectedItem=item;}panel.Children.Add(scene);
  Note("Behemoth bonuses to all heroes",true);
  var sourcePicker=new ComboBox{Width=320,HorizontalAlignment=HorizontalAlignment.Left};
  foreach(var pair in new[]{("manual","Manual combined bonus snapshot"),("configured","Configured level + star base bonuses")}){var item=new ComboBoxItem{Content=pair.Item2,Tag=pair.Item1};sourcePicker.Items.Add(item);if(pair.Item1==current.BehemothSource)sourcePicker.SelectedItem=item;}panel.Children.Add(sourcePicker);
  Note("Choose one source. Configured rows count current level and star benefits once; skills, talents, breakthrough/full-skill bonuses remain excluded. Exact star step is a configuration progression index, not the displayed star count.");
  Note("Enter combined flat hero-stat bonuses granted by your Behemoths. Do not enter a Behemoth's own ATK/DEF/HP or benefits already recorded as Research. Level alone does not identify all owned/talent/skill bonuses.");
  var statPanel=new WrapPanel();panel.Children.Add(statPanel);var statEditors=new List<TextBox>();
  for(int i=0;i<3;i++){var input=new TextBox{Text=current.Behemoth[i]?.ToString(CultureInfo.InvariantCulture)??"",Width=150,Padding=new Thickness(6)};Field(statPanel,new[]{"ATK bonus","DEF bonus","HP bonus"}[i],input);statEditors.Add(input);}
  var selectors=new Dictionary<string,Dictionary<string,ComboBox>>();
  void Catalog(string title,string explanation,string kind,Dictionary<string,ArmyContextEntry> catalog,Dictionary<string,int> values)
  {
   var body=new StackPanel();var expander=new Expander{Header=title,Content=body,Foreground=Brushes.White,Margin=new Thickness(0,10,0,6)};panel.Children.Add(expander);body.Children.Add(CopyText(explanation));
   var search=new TextBox{Margin=new Thickness(0,2,0,6),ToolTip="Filter by name"};body.Children.Add(search);
   var description=CopyText("");
   var rows=new StackPanel();body.Children.Add(new ScrollViewer{Content=rows,MaxHeight=300,VerticalScrollBarVisibility=ScrollBarVisibility.Auto});
   selectors[kind]=[];var filters=new List<(FrameworkElement Row,string Name)>();
   foreach(var (key,entry) in catalog.OrderBy(x=>x.Value.Name))
   {
    string label=kind=="signature"?(_heroes.Find(h=>h.AssetSlug==key)?.Name??key)+" — "+entry.Name:entry.Name;
    var row=new Grid{Margin=new Thickness(0,3,0,3)};row.ColumnDefinitions.Add(new ColumnDefinition());row.ColumnDefinitions.Add(new ColumnDefinition{Width=new GridLength(155)});
    row.Children.Add(CopyText(label));var picker=new ComboBox{MinWidth=140,VerticalAlignment=VerticalAlignment.Center};Grid.SetColumn(picker,1);row.Children.Add(picker);
    picker.Items.Add(new ComboBoxItem{Content="Excluded / unknown",Tag=0});picker.SelectedIndex=0;
    foreach(var level in entry.Levels){var item=new ComboBoxItem{Content=(kind=="behemoth-star"?"Config step ":"Level ")+level.Level,Tag=level.Level};picker.Items.Add(item);if(values.GetValueOrDefault(key)==level.Level)picker.SelectedItem=item;}
    if(kind=="signature")picker.SelectionChanged+=(_,_)=>{int n=(int)((ComboBoxItem)picker.SelectedItem).Tag;var selected=entry.Levels.Find(r=>r.Level==n);description.Text=selected?.Description.Length>0?selected.Description+" (configured description; effect not yet included in score)":"";};
    System.Windows.Automation.AutomationProperties.SetName(picker,kind+" "+key);selectors[kind][key]=picker;rows.Children.Add(row);filters.Add((row,(label+" "+key).ToLowerInvariant()));
   }
   body.Children.Add(description);
   search.TextChanged+=(_,_)=>{foreach(var (row,name) in filters)row.Visibility=name.Contains(search.Text.ToLowerInvariant())?Visibility.Visible:Visibility.Collapsed;};
  }
  Catalog("Configured Behemoth levels","Record only Behemoths whose bonuses apply to this march/encounter.","behemoth-level",_armyContextData.Behemoths,current.BehemothBuilds.ToDictionary(x=>x.Key,x=>x.Value.Level));
  Catalog("Configured Behemoth star progression","Exact config step, not a displayed star count. Unknown steps remain excluded.","behemoth-star",_armyContextData.Behemoths.ToDictionary(x=>x.Key,x=>new ArmyContextEntry{Name=x.Value.Name,Levels=x.Value.Stars}),current.BehemothBuilds.ToDictionary(x=>x.Key,x=>x.Value.Star));
  void SourceState(){bool manual=(string)((ComboBoxItem)sourcePicker.SelectedItem).Tag=="manual";foreach(var input in statEditors)input.IsEnabled=manual;foreach(var kind in new[]{"behemoth-level","behemoth-star"})foreach(var picker in selectors[kind].Values)picker.IsEnabled=!manual;}
  sourcePicker.SelectionChanged+=(_,_)=>SourceState();SourceState();
  Catalog("Signature Gear — My builds only","Adds the selected level's hero stats. Signature linked battle skills and extra effects remain excluded.","signature",_armyContextData.Signature,current.Signature);
  Catalog("Research — traced hero-stat effects","Select current levels, not every completed level. Role, faction and encounter restrictions apply. Troop multipliers and other effects are excluded.","research",_armyContextData.Research,current.Research);
  Note("Partial model: Behemoth battle skills/own damage, Signature linked skills and troop multipliers are not simulated. Upgrade-cost/stat-return panels compare their named raw contributions without this context.");
  var error=CopyText("");error.Foreground=Brushes.Orange;panel.Children.Add(error);
  var buttons=new WrapPanel();panel.Children.Add(buttons);var apply=new Button{Content="Apply",Padding=new Thickness(18,8,18,8),Margin=new Thickness(0,0,12,0)};buttons.Children.Add(apply);var cancel=new Button{Content="Cancel",Padding=new Thickness(18,8,18,8)};buttons.Children.Add(cancel);cancel.Click+=(_,_)=>window.Close();
  apply.Click+=(_,_)=>{
   double?[] stats=new double?[3];for(int i=0;i<3;i++){if(string.IsNullOrWhiteSpace(statEditors[i].Text))continue;if(!double.TryParse(statEditors[i].Text,NumberStyles.Float,CultureInfo.InvariantCulture,out double v)||!double.IsFinite(v)||v<0||v>1e12){error.Text="Enter finite, non-negative Behemoth bonuses, or leave blank.";return;}stats[i]=v;}
   Dictionary<string,int> Values(string kind)=>selectors[kind].ToDictionary(x=>x.Key,x=>(int)((ComboBoxItem)x.Value.SelectedItem).Tag).Where(x=>x.Value>0).ToDictionary();
   var old=_armyContext;_armyContext=ArmyContextModel.Clean(new(){Enabled=enabled.IsChecked==true,Scene=(string)((ComboBoxItem)scene.SelectedItem).Tag,Behemoth=stats,BehemothSource=(string)((ComboBoxItem)sourcePicker.SelectedItem).Tag,BehemothBuilds=_armyContextData.Behemoths.Keys.ToDictionary(key=>key,key=>new ArmyBehemothBuild{Level=Values("behemoth-level").GetValueOrDefault(key),Star=Values("behemoth-star").GetValueOrDefault(key)}),Research=Values("research"),Signature=Values("signature")},_armyContextData);
   try{SaveProfile();}catch(Exception ex){_armyContext=old;error.Text="Settings were not saved: "+ex.Message;return;}
   RefreshEstimates();RebuildOptimizer();UpdateSquadPresentation();if(_activeHero is not null)RefreshSignaturePanels(_activeHero);if(InspectorTabs.SelectedIndex==5)RenderBehemoths();_researchEdits.Clear();if(InspectorTabs.SelectedIndex==6)RenderResearch();window.Close();
  };
  window.ShowDialog();
 }
}
