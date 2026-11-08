namespace TilesSurviveHeroPlanner;

public sealed class FactionTalentBranch
{
 public string Name {get;set;}=""; public int Faction {get;set;} public bool Enabled {get;set;}
 public Dictionary<string,FactionTalentNode> Nodes {get;set;}=[];
}
public sealed class FactionTalentNode
{
 public string Name {get;set;}=""; public string IconAsset {get;set;}=""; public int Type {get;set;}
 public List<FactionTalentLevel> Levels {get;set;}=[];
}
public sealed class FactionTalentLevel:ArmyContextLevel
{
 public int Id {get;set;} public int Cost {get;set;} public List<int> Requires {get;set;}=[];
}
public sealed record FactionTalentChoice(string Key,string Name,int Level,int Cost,double Gain,double GainPerPoint,bool Modeled);
public sealed record FactionTalentGuide(string Branch,string Kind,FactionTalentChoice? Choice,string Message,int Shortfall=0);
public static class FactionTalentModel
{
 public static List<FactionTalentGuide> Guidance(ArmyContextSettings s,ArmyContextData data,List<FactionTalentChoice> scored)
 {
  List<FactionTalentGuide> result=[];
  foreach(var (branch,b) in data.FactionTalents){
   if(Errors(s,data,branch).Count>0){result.Add(new(branch,"invalid",null,"Check recorded levels and point totals."));continue;}
   if(!s.FactionPoints.TryGetValue(branch,out int total)||total<0||total>100000){result.Add(new(branch,"unknown",null,"Enter total Star Points for this faction."));continue;}
   int available=total-Spent(branch,s,data);var best=scored.FirstOrDefault(c=>c.Key.StartsWith(branch+":")&&c.Modeled&&c.Gain>0);
   if(best is not null){result.Add(new(branch,"scored",best,"Ranked by selected-squad hero-score gain per point."));continue;}
   var legal=new List<(string Serial,FactionTalentNode Node,FactionTalentLevel Row)>();
   foreach(var (serial,node) in b.Nodes){string key=branch+":"+serial;var row=node.Levels.Find(r=>r.Level==s.FactionTalents.GetValueOrDefault(key)+1);if(row is null)continue;
    var candidate=new ArmyContextSettings{FactionTalents=new(s.FactionTalents)};candidate.FactionTalents[key]=row.Level;
    if(Errors(candidate,data,branch).Count==0)legal.Add((serial,node,row));
   }
   if(legal.Count==0){bool full=b.Nodes.All(n=>s.FactionTalents.GetValueOrDefault(branch+":"+n.Key)==n.Value.Levels.Last().Level);result.Add(new(branch,full?"complete":"locked",null,full?"All configured talent levels are recorded.":"No unlocked next level. Check prerequisite levels."));continue;}
   var affordable=legal.Where(x=>x.Row.Cost<=available).OrderBy(x=>int.Parse(x.Serial)).ToList();
   var target=affordable.Count>0?affordable[0]:legal.OrderBy(x=>x.Row.Cost-available).ThenBy(x=>int.Parse(x.Serial)).First();
   var choice=new FactionTalentChoice(branch+":"+target.Serial,b.Name+" · "+target.Node.Name,target.Row.Level,target.Row.Cost,0,0,target.Row.Effects.Count>0);
   if(affordable.Count==0){int missing=target.Row.Cost-available;var owned=new Dictionary<string,int>(s.FactionTalents){[branch+":"+target.Serial]=target.Row.Level};
    var ids=b.Nodes.SelectMany(n=>n.Value.Levels.Select(r=>(r.Id,Key:branch+":"+n.Key,Row:r))).ToDictionary(r=>r.Id);
    var unlocks=b.Nodes.Where(n=>s.FactionTalents.GetValueOrDefault(branch+":"+n.Key)==0&&n.Value.Levels[0].Requires.Contains(target.Row.Id)&&n.Value.Levels[0].Requires.All(id=>ids.TryGetValue(id,out var p)&&owned.GetValueOrDefault(p.Key)>=p.Row.Level)).Select(n=>n.Value.Name);
    string message=$"Save {missing} more points for {target.Node.Name} Lv {target.Row.Level}: costs {target.Row.Cost}, available {available}.";if(unlocks.Any())message+=" Unlocks "+string.Join(", ",unlocks)+".";
    result.Add(new(branch,"save",choice,message,missing));
   }else if(target.Node.Type==3)result.Add(new(branch,"review",choice,"Conditional effect is unverified. Review before spending; no numerical ranking."));
   else result.Add(new(branch,"progression",choice,target.Row.Description+". Unlock-order guide; combat gain not quantified."));
  }
  return result;
 }
 public static int Spent(string branch,ArmyContextSettings s,ArmyContextData data)=>data.FactionTalents[branch].Nodes.Sum(pair=>pair.Value.Levels.Where(r=>r.Level<=s.FactionTalents.GetValueOrDefault(branch+":"+pair.Key)).Sum(r=>r.Cost));
 public static List<string> Errors(ArmyContextSettings s,ArmyContextData data,string branch)
 {
  List<string> errors=[];var b=data.FactionTalents[branch];
  var ids=b.Nodes.SelectMany(p=>p.Value.Levels.Select(r=>(r.Id,Key:branch+":"+p.Key,Row:r))).ToDictionary(x=>x.Id);
  foreach(var (serial,node) in b.Nodes){int n=s.FactionTalents.GetValueOrDefault(branch+":"+serial);if(n==0)continue;
   if(!b.Enabled||!node.Levels.Any(r=>r.Level==n)){errors.Add(node.Name+": invalid level");continue;}
   foreach(var row in node.Levels.Where(r=>r.Level<=n))foreach(int pre in row.Requires)
    if(!ids.TryGetValue(pre,out var p)||s.FactionTalents.GetValueOrDefault(p.Key)<p.Row.Level)errors.Add(node.Name+": prerequisite missing");
  }
  if(s.FactionPoints.TryGetValue(branch,out int total)&&total>=0&&total<=100000&&Spent(branch,s,data)>total)errors.Add(b.Name+": exceeds total Star Points");
  return errors.Distinct().ToList();
 }
 public static Dictionary<string,int> ValidSelections(ArmyContextSettings s,ArmyContextData data)
 {
  s.FactionTalents??=[];s.FactionPoints??=[];Dictionary<string,int> result=[];
  foreach(var (branch,b) in data.FactionTalents)if(Errors(s,data,branch).Count==0)foreach(var serial in b.Nodes.Keys){string key=branch+":"+serial;int n=s.FactionTalents.GetValueOrDefault(key);if(n>0)result[key]=n;}
  return result;
 }
 public static List<FactionTalentChoice> Recommend(ArmyContextSettings s,ArmyContextData data,Func<ArmyContextSettings,double> score)
 {
  List<FactionTalentChoice> result=[];double baseline=score(s);
  foreach(var (branch,b) in data.FactionTalents){if(!s.FactionPoints.TryGetValue(branch,out int total)||total<0||total>100000)continue;int available=total-Spent(branch,s,data);
   foreach(var (serial,node) in b.Nodes){string key=branch+":"+serial;int n=s.FactionTalents.GetValueOrDefault(key);var row=node.Levels.Find(r=>r.Level==n+1);if(row is null||row.Cost>available)continue;
    var next=System.Text.Json.JsonSerializer.Deserialize<ArmyContextSettings>(System.Text.Json.JsonSerializer.Serialize(s))!;next.FactionTalents[key]=n+1;if(Errors(next,data,branch).Count>0)continue;
    double gain=Math.Max(0,score(next)-baseline);result.Add(new(key,b.Name+" · "+node.Name,n+1,row.Cost,gain,gain/row.Cost,row.Effects.Count>0));
   }
  }
  return result.OrderBy(r=>r.Key.Split(':')[0],StringComparer.Ordinal).ThenByDescending(r=>r.GainPerPoint).ThenBy(r=>r.Key,StringComparer.Ordinal).ToList();
 }
}
