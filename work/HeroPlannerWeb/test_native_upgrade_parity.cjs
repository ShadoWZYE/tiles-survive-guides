const test=require('node:test'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),path=require('node:path');
const model=require('./upgrade-model.js'),data=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json');
test('native C# and browser model agree across real rank steps and all return metrics',()=>{
  const root=path.resolve(__dirname,'../..');
  const cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','unused','--upgrades',path.join(root,'outputs/hero-report/TilesSurvive-Upgrade-Data.json')],{encoding:'utf8'}));
  assert.equal(cases.length,60);
  for(const c of cases){
    const js=model.evaluate(c.slugs,c.builds,data,c.settings);
    assert.deepEqual(js.missing,c.missing,c.id);
    assert.equal(js.candidates.length,c.candidates.length,c.id);
    for(const n of c.candidates){
      const j=js.candidates.find(x=>x.slug===n.slug&&x.label===n.label);assert.ok(j,`${c.id}: ${n.label}`);
      for(const key of ['gain','efficiency']){
        if(n[key]===null)assert.equal(j[key],null,`${c.id} ${key}`);
        else assert.ok(Math.abs(j[key]-n[key])<1e-8,`${c.id} ${n.label} ${key}`);
      }
      assert.deepEqual(j.cost,n.cost);assert.equal(j.group,n.group);assert.equal(j.affordability,n.affordability);
      assert.equal(j.unsupported,n.unsupported);assert.equal(Boolean(j.blocked),Boolean(n.blocked));
      if(n.delta!==null)n.delta.forEach((v,i)=>assert.ok(Math.abs(j.delta[i]-v)<1e-8));else assert.equal(j.delta,null);
    }
  }
});
