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
public static class FactionTalentModel
{
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
