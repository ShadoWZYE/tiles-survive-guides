using System.Text.Json;
namespace TilesSurviveHeroPlanner;
public sealed class ArmyContextData
{
 public Dictionary<string,string> FactionTalentSourceHashes {get;set;}=[];
 public Dictionary<string,FactionTalentBranch> FactionTalents {get;set;}=[];
 public Dictionary<string,string> SourceHashes {get;set;}=[];
 public BehemothStarDisplay BehemothStarDisplay {get;set;}=new();
 public Dictionary<string,ArmyResearchTree> ResearchTrees {get;set;}=[];
 public Dictionary<string,ArmyContextEntry> Signature {get;set;}=[];
 public Dictionary<string,ArmyContextEntry> Research {get;set;}=[];
 public Dictionary<string,ArmyContextEntry> Behemoths {get;set;}=[];
 public Dictionary<string,ArmyHeroScope> Heroes {get;set;}=[];
 public static ArmyContextData Parse(string json)=>JsonSerializer.Deserialize<ArmyContextData>(json,new JsonSerializerOptions{PropertyNamingPolicy=JsonNamingPolicy.SnakeCaseLower})!;
}
public sealed class BehemothStarDisplay {public int Tiers {get;set;}=12;public int Slots {get;set;}=5;public int StepsPerStar {get;set;}=6;public int StepsPerTier {get;set;}=30;}
public sealed class ArmyResearchTree {public string Name {get;set;}="";public bool Legacy {get;set;} public bool Gated {get;set;} public string AvailabilityNote {get;set;}=""; public int Order {get;set;}}
public sealed class ArmyHeroScope {public string Role {get;set;}="";public string Faction {get;set;}="";}
public sealed class ArmyContextEntry {public string Tree {get;set;}=""; public int Tier {get;set;} public int Row {get;set;} public string AvailabilityNote {get;set;}=""; public string IconAsset {get;set;}=""; public string SkillIconAsset {get;set;}=""; public string SkillName {get;set;}=""; public string Name {get;set;}="";public List<ArmyContextLevel> Levels {get;set;}=[];public List<ArmyContextLevel> Stars {get;set;}=[];}
public class ArmyContextLevel {public int Level {get;set;} public List<ArmyContextEffect> Effects {get;set;}=[];public List<string> Unmodeled {get;set;}=[];public bool LinkedSkill {get;set;} public string Description {get;set;}="";}
public sealed class ArmyContextEffect {public string Scope {get;set;}="all";public string Scene {get;set;}="all";public int Stat {get;set;} public double Value {get;set;}}
public sealed class ArmyContextSettings
{
 public Dictionary<string,int> FactionTalents {get;set;}=[];
 public Dictionary<string,int> FactionPoints {get;set;}=[];
 public string BehemothSource {get;set;}="manual";
 public Dictionary<string,ArmyBehemothBuild> BehemothBuilds {get;set;}=[];
 public bool Enabled {get;set;}
 public string Scene {get;set;}="all";
 public Dictionary<string,int> Research {get;set;}=[];
 public Dictionary<string,int> Signature {get;set;}=[];
 public double?[] Behemoth {get;set;}=[null,null,null];
}
public sealed class ArmyBehemothBuild {public int Level {get;set;} public int Star {get;set;}}
public sealed record ArmyContextResult(double[] Flat,List<string> Notes,bool Active);
public static class ArmyContextModel
{
 public static ArmyContextSettings Clean(ArmyContextSettings? raw,ArmyContextData data)
 {
  raw??=new();
  Dictionary<string,int> Selected(Dictionary<string,int>? values,Dictionary<string,ArmyContextEntry> catalog)=>(values??[]).Where(x=>catalog.TryGetValue(x.Key,out var row)&&row.Levels.Any(r=>r.Level==x.Value)).ToDictionary();
  Dictionary<string,ArmyBehemothBuild> beasts=[];
  foreach(var (key,value) in raw.BehemothBuilds??[]){if(!data.Behemoths.TryGetValue(key,out var entry)||value is null)continue;int level=entry.Levels.Any(r=>r.Level==value.Level)?value.Level:0,star=entry.Stars.Any(r=>r.Level==value.Star)?value.Star:0;if(level>0||star>0)beasts[key]=new(){Level=level,Star=star};}
  var talents=FactionTalentModel.ValidSelections(raw,data);
  return new(){FactionTalents=talents,FactionPoints=(raw.FactionPoints??[]).Where(x=>data.FactionTalents.ContainsKey(x.Key)&&x.Value>=0&&x.Value<=100000).ToDictionary(),Enabled=raw.Enabled,Scene=raw.Scene is "pve" or "gve"?raw.Scene:"all",BehemothSource=raw.BehemothSource=="configured"?"configured":"manual",BehemothBuilds=beasts,Research=Selected(raw.Research,data.Research),Signature=Selected(raw.Signature,data.Signature),Behemoth=Enumerable.Range(0,3).Select(i=>raw.Behemoth?.ElementAtOrDefault(i) is double v&&double.IsFinite(v)&&v>=0&&v<=1e12?(double?)v:null).ToArray()};
 }
 public static ArmyContextResult Resolve(string slug,ArmyContextSettings? raw,ArmyContextData data,string basis="reference")
 {
  var s=Clean(raw,data);double[] flat=[0,0,0];List<string> notes=[];
  if(!s.Enabled||basis=="flat")return new(flat,notes,false);
  var hero=data.Heroes.GetValueOrDefault(slug)??new();
  void Apply(ArmyContextLevel row,string label){
   foreach(var e in row.Effects)if((e.Scope=="all"||e.Scope==hero.Role||e.Scope==hero.Faction)&&(e.Scene=="all"||e.Scene==s.Scene))flat[e.Stat]+=e.Value;
   if(row.LinkedSkill)notes.Add(label+": linked skill excluded");
   if(row.Unmodeled.Count>0)notes.Add(label+": additional effects excluded");
  }
  if(s.BehemothSource=="manual")for(int i=0;i<3;i++)flat[i]+=s.Behemoth[i]??0;
  else foreach(var (key,build) in s.BehemothBuilds){var entry=data.Behemoths[key];foreach(var row in new[]{entry.Levels.Find(r=>r.Level==build.Level),entry.Stars.Find(r=>r.Level==build.Star)})if(row is not null)Apply(row,entry.Name);notes.Add(entry.Name+": level/star stats only; skill, talent and full-skill bonuses excluded");}
  foreach(var (key,n) in s.Research)Apply(data.Research[key].Levels.First(r=>r.Level==n),data.Research[key].Name);
  foreach(var (key,n) in s.FactionTalents){var parts=key.Split(':');Apply(data.FactionTalents[parts[0]].Nodes[parts[1]].Levels.First(r=>r.Level==n),"Faction talent");}
  if(basis=="recorded"&&s.Signature.TryGetValue(slug,out int level))Apply(data.Signature[slug].Levels.First(r=>r.Level==level),"Signature Gear");
  return new(flat,notes,true);
 }
}

public sealed record BehemothStarSlot(int Base,int Overlay,int Steps);
public static class BehemothStarProgress
{
 public static readonly string[] Colors=["Green","Blue","Purple","Gold","Red","Red+","Orange","Orange+","Platinum","Platinum+","Rainbow","Rainbow+"];
 public static List<BehemothStarSlot> Slots(int count,int tiers=12){int tier=Math.Min(count/30+1,tiers),n=count%30;bool full=count/30+1>tiers;List<BehemothStarSlot> slots=[];for(int i=0;i<5;i++){slots.Add(new(tier-1,tier,full?6:Math.Min(6,n)));n=Math.Max(0,n-6);}return slots;}
 public static string Color(int phase)=>phase<=Colors.Length?Colors[phase-1]:"Advanced phase "+phase;
 public static string Label(int count)=>count==0?"Stars unknown":$"{Color((count-1)/30+1)} · star {((count-1)%30)/6+1} · step {(count-1)%6+1}/6";
}
