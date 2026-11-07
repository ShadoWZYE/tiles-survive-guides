using System.Text.Json;
using System.Text.Json.Serialization;
namespace TilesSurviveHeroPlanner;
public sealed class SurvivalBenchmarkData
{
    public double Pressure {get;set;}
    [JsonPropertyName("back_share")] public double BackShare {get;set;}
    public static SurvivalBenchmarkData Parse(string json)=>JsonSerializer.Deserialize<SurvivalBenchmarkData>(json,new JsonSerializerOptions{PropertyNameCaseInsensitive=true})!;
}
public sealed record SurvivalProjection(double[] DeathTimes,double[] AliveSeconds,bool[] Censored,double Horizon,double Adjustment=0,bool Available=true);
public static class SurvivalModel
{
    public static SurvivalProjection Project(double[] hp,double pressure,double backShare,double horizon=30)
    {
        if(hp.Length!=5||hp.Any(v=>!double.IsFinite(v)||v<0)||!double.IsFinite(pressure)||pressure<=0||!double.IsFinite(backShare)||backShare<0||backShare>1||!double.IsFinite(horizon)||horizon<=0)throw new ArgumentException("Invalid survival scenario");
        var remaining=hp.ToArray();var dead=hp.Select(v=>v==0).ToArray();double[] deaths=new double[5];double time=0;
        for(int e=0;e<5&&dead.Any(v=>!v);e++){
            int front=Enumerable.Range(0,2).Count(i=>!dead[i]),back=Enumerable.Range(2,3).Count(i=>!dead[i]);double[] rates=new double[5];double dt=double.PositiveInfinity;
            for(int i=0;i<5;i++)if(!dead[i]){rates[i]=i<2?pressure*(back>0?1-backShare:1)/front:pressure*(front>0?backShare:1)/back;if(rates[i]>0)dt=Math.Min(dt,remaining[i]/rates[i]);}
            if(!double.IsFinite(dt))throw new ArgumentException("Scenario has no reachable target");time+=dt;
            for(int i=0;i<5;i++)if(!dead[i]){remaining[i]=Math.Max(0,remaining[i]-rates[i]*dt);if(remaining[i]<=1e-9*Math.Max(1,hp[i])){dead[i]=true;deaths[i]=time;}}
        }
        return new(deaths,deaths.Select(t=>Math.Min(t,horizon)).ToArray(),deaths.Select(t=>t>=horizon).ToArray(),horizon);
    }
    public static SurvivalProjection Evaluate(IReadOnlyList<Hero> heroes,PlannerMode mode,SurvivalBenchmarkData? data,double horizon=30)
    {
        SurvivalProjection unavailable=new([],[],[],horizon,0,false);
        if(heroes.Count!=5||data is null||data.Pressure<=0)return unavailable;
        double team=heroes.Sum(h=>h.Estimate?.TeamPercent?.ElementAtOrDefault(2)??0);
        double[] hp=heroes.Select(h=>{var e=h.Estimate;double self=e?.SelfPercent?.ElementAtOrDefault(2)??0,own=e?.TeamPercent?.ElementAtOrDefault(2)??0;return (e?.HeroStats?.ElementAtOrDefault(2)??0)*(1+(team-own)/(1+self+own));}).ToArray();
        if(hp.Any(v=>!double.IsFinite(v)||v<=0))return unavailable;
        var result=Project(hp,data.Pressure,data.BackShare,horizon);double weight=mode switch{PlannerMode.Offense=>.8875,PlannerMode.Survival=>.1375,PlannerMode.Pve=>.5875,_=>.55};
        return result with {Adjustment=weight*heroes.Select((h,i)=>Math.Max(0,h.OffenseIndex)*(result.AliveSeconds[i]/horizon-1)).Average()};
    }
}
