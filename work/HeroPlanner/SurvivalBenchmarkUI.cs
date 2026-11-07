using System.IO;
using System.Windows;
using System.Windows.Controls;
namespace TilesSurviveHeroPlanner;
public partial class MainWindow
{
    private bool _survivalBenchmark;
    private SurvivalBenchmarkData _survivalData=new();
    private SurvivalBenchmarkData? ActiveSurvivalData=>_survivalBenchmark&&_comparisonBasis=="recorded"?_survivalData:null;
    private int SurvivalHorizon=>_battleSeconds>0?_battleSeconds:30;
    private void LoadSurvivalData(){using var reader=new StreamReader(Application.GetResourceStream(new Uri("pack://application:,,,/TilesSurviveHeroPlanner;component/Data/survival.json"))!.Stream);_survivalData=SurvivalBenchmarkData.Parse(reader.ReadToEnd());}
    private void Survival_Changed(object sender,RoutedEventArgs e){if(_loadingProfile||_heroes.Count==0)return;_survivalBenchmark=SurvivalToggle.IsChecked==true;SaveProfile();RebuildOptimizer();UpdateRecommendations();UpdateSquadPresentation();}
    private void RefreshSurvivalNotice()
    {
        bool wasLoading=_loadingProfile;_loadingProfile=true;try{SurvivalToggle.IsChecked=_survivalBenchmark;SurvivalToggle.IsEnabled=_comparisonBasis=="recorded";}finally{_loadingProfile=wasLoading;}
        SurvivalNotice.Text=ActiveSurvivalData is null?"Optional: select My builds to compare HP survival under a fixed reference pressure.":"Experimental reference pressure learned from one PvP replay (presentation-time reference; combat-clock equivalence unverified); not your target's known damage. Unknown troop HP, healing, shields, control and per-target mitigation are excluded. Personal offense is discounted by predicted exposure; other score components are retained.";
        if(ActiveSurvivalData is not null&&_selected.Count==5){var squad=OrderForFormation(_selected,CurrentMode).ToArray();var p=SurvivalModel.Evaluate(squad,CurrentMode,ActiveSurvivalData,SurvivalHorizon);if(p.Available)SurvivalNotice.Text+="\nReference survival: "+string.Join(" · ",squad.Select((h,i)=>$"{h.Name} {p.AliveSeconds[i]:0.0}{(p.Censored[i]?"+":"")}s"))+". + means alive at the window limit.";}
    }
    private List<SquadResult> FindCurrentSquads(IReadOnlyList<Hero> pool,PlannerMode mode,bool coverage,int limit,string enemy)=>FindTopSquadsCore(pool,mode,coverage,limit,enemy,ActiveSurvivalData,SurvivalHorizon);
}
