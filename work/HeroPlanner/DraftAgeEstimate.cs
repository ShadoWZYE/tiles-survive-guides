using System.Windows;
using System.Windows.Controls;
namespace TilesSurviveHeroPlanner;
public partial class MainWindow
{
    private void RefreshDraftAgeEstimate()
    {
        if(DraftAgePanel is null)return;
        DraftAgePanel.Children.Clear();
        var picker=new ComboBox{MaxWidth=550,HorizontalAlignment=HorizontalAlignment.Left};
        picker.Items.Add(new Choice(null,"Current Targeted Draft · select the live pool"));
        foreach(var pool in (_upgradeData.TargetedDraft?.Pools??[]).DistinctBy(p=>string.Join(',',p.Choices.Select(c=>c.Slug))))
            picker.Items.Add(new Choice(pool.Id,string.Join(", ",pool.Choices.Select(c=>_upgradeData.Heroes.GetValueOrDefault(c.Slug)?.Name??c.Slug))));
        picker.SelectedItem=picker.Items.Cast<Choice>().FirstOrDefault(c=>c.Id==_upgradeSettings.TargetedPool)??picker.Items[0];
        DraftAgePanel.Children.Add(picker);var note=CopyText("");DraftAgePanel.Children.Add(note);
        void Update(){
            var pool=_upgradeData.TargetedDraft?.Pools.Find(p=>p.Id==(picker.SelectedItem as Choice)?.Id);
            var newest=pool?.Choices.Select(c=>_heroes.Find(h=>h.AssetSlug==c.Slug)).Where(h=>h?.ReleaseWeekMin is not null).OrderByDescending(h=>h!.ReleaseWeekMin).FirstOrDefault();
            if(newest is null){note.Text="Choose the exact live draft. After a merge, event age can differ from the state's original opening date.";return;}
            int first=newest.ReleaseWeekMin!.Value,last=newest.ReleaseWeekMax??first;
            var low=DateTime.Today.AddDays(-(last*7-1));var high=DateTime.Today.AddDays(-(first-1)*7);
            note.Text=$"Draft age clue: {newest.Name} has configured introduction weeks {first}–{last}. If this is its introduction cycle, the effective opening date is approximately {low:d MMM yyyy} – {high:d MMM yyyy}. This is a conditional range, not a verified draft schedule: older heroes remain available, and merged-server overrides are unknown. The current saved date is not overwritten.";
        }
        picker.SelectionChanged+=(_,_)=>{_upgradeSettings.TargetedPool=(picker.SelectedItem as Choice)?.Id;if(!_loadingProfile)SaveProfile();Update();};Update();
    }
}
