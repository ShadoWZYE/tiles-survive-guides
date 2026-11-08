using System.Windows;

using System.Windows.Controls;

using System.Windows.Media;



namespace TilesSurviveHeroPlanner;

public partial class MainWindow

{

    private string ReviewSnapshotKey=>_upgradeData.ClientBuild+"|"+string.Join("|",_upgradeData.SourceHashes.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>x.Key+":"+x.Value));
    private string AccountReviewSnapshotKey=>ReviewSnapshotKey+"|standalone|"+string.Join("|",_armyContextData.SourceHashes.Concat(_armyContextData.FactionTalentSourceHashes.Select(x=>new KeyValuePair<string,string>("faction-talents:"+x.Key,x.Value))).OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>x.Key+":"+x.Value));
    private AccountDataReview? _accountReview;
    private string AccountContentHash()=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(System.Text.Json.JsonSerializer.Serialize(_armyContext))));
    private bool AccountReviewFresh=>_accountReview is not null && _accountReview.ClientBuild==AccountReviewSnapshotKey && _accountReview.ContentHash==AccountContentHash() && _accountReview.ReviewedUtc<=DateTimeOffset.UtcNow.AddMinutes(5) && DateTimeOffset.UtcNow-_accountReview.ReviewedUtc<TimeSpan.FromDays(14);
    private void RefreshSquadDataNotice()

    {

        SquadDataNotice.Children.Clear();

        var missing=_selected.Select(h=>new{Hero=h,Fields=EstimateModel.MissingBuild(h.AssetSlug,_heroBuilds.GetValueOrDefault(h.AssetSlug),_upgradeData)}).Where(x=>x.Fields.Count>0).ToList();

        var stale=_selected.Where(h=>EstimateModel.MissingBuild(h.AssetSlug,_heroBuilds.GetValueOrDefault(h.AssetSlug),_upgradeData).Count==0)

            .Select(h=>new {Hero=h,Build=_heroBuilds.GetValueOrDefault(h.AssetSlug)!})

            .Where(x=>x.Build.ReviewedUtc is null || x.Build.ReviewedUtc>DateTimeOffset.UtcNow.AddMinutes(5) || DateTimeOffset.UtcNow-x.Build.ReviewedUtc>TimeSpan.FromDays(14) || x.Build.ReviewedClientBuild!=ReviewSnapshotKey).ToList();

        var account=new List<string>();

        if(!_armyContext.Enabled)account.Add("Army bonuses disabled");

        if(_armyContext.FactionTalents.Count==0)account.Add("Faction talents not recorded (if unlocked)");
        if(_armyContext.Research.Count==0)account.Add("Research not recorded");

        if(_armyContext.BehemothSource=="configured" ? !_armyContext.BehemothBuilds.Values.Any(b=>b.Level>0||b.Star>0) : _armyContext.Behemoth.All(v=>v is null))account.Add("Behemoth bonuses not recorded");

        if(_comparisonBasis=="recorded"&&!_selected.Any(h=>_armyContext.Signature.ContainsKey(h.AssetSlug)))account.Add("Signature Gear not recorded (if owned)");

        if(AccountReviewFresh)account.Clear();else account.Add("Account bonus values need an in-game review (unconfirmed, changed or older than 14 days)");
        if(missing.Count==0&&stale.Count==0&&_selected.Count>0&&account.Count==0)return;

        var body=new StackPanel();

        string heading=_selected.Count==0?"Complete your squad data · select heroes first":missing.Count>0?$"Complete your squad data · {missing.Count} incomplete builds":stale.Count>0?$"Review squad data · {stale.Count} builds need revalidation":"Check your account bonus data";

        SquadDataNotice.Children.Add(new Expander{Header=heading,Content=body,Foreground=Brushes.Gold});

        body.Children.Add(CopyText(_comparisonBasis=="recorded"?"Please fill in missing build values. Unknown level uses 1; unrecorded or locked upgrades add no bonus.":"This is a maximum-build comparison, not your current squad strength. Record your builds and select My builds for personal recommendations."));

        if(_selected.Count==0)body.Children.Add(CopyText("Select heroes, then record their level, exact rank/step, unlocked skills and equipped gear (or explicitly none)."));

        foreach(var item in missing){var button=new Button{Content="Fill missing data · "+item.Hero.Name,Tag=item.Hero,HorizontalContentAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,2,0,3),Padding=new Thickness(8,5,8,5)};button.Click+=(_,e)=>EditBuild_Click(button,e);body.Children.Add(button);body.Children.Add(CopyText(string.Join(", ",item.Fields)));}

        foreach(var item in stale){var button=new Button{Content="Review in game · "+item.Hero.Name,Tag=item.Hero,HorizontalContentAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,2,0,3)};button.Click+=(_,e)=>EditBuild_Click(button,e);body.Children.Add(button);body.Children.Add(CopyText(item.Build.ReviewedUtc is null?"No in-game review recorded. Confirm current values in the build editor.":item.Build.ReviewedClientBuild!=ReviewSnapshotKey?"Game data changed since the last review.":"Last reviewed "+item.Build.ReviewedUtc.Value.ToLocalTime().ToString("yyyy-MM-dd")+". Check values again (14-day reminder)."));}

        if(account.Count>0){body.Children.Add(CopyText(string.Join(" · ",account)));var confirm=new Button{Content="I checked Research, Behemoths and Signature Gear",HorizontalContentAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,3,0,5)};
            confirm.Click+=(_,_)=>{var old=_accountReview;_accountReview=new(){ReviewedUtc=DateTimeOffset.UtcNow,ClientBuild=AccountReviewSnapshotKey,ContentHash=AccountContentHash()};try{SaveProfile();RefreshSquadDataNotice();}catch(System.IO.IOException){_accountReview=old;}catch(UnauthorizedAccessException){_accountReview=old;}};body.Children.Add(confirm);body.Children.Add(CopyText("Confirm only after checking the account sections. Unowned or unavailable sources can stay blank; confirming gives them no bonus. Any account-setting change requests another review."));}

        body.Children.Add(CopyText("Also record owned Signature Gear, Research and Behemoths in their sections. Leave unavailable or unowned bonuses blank; they are excluded."));

    }

}
