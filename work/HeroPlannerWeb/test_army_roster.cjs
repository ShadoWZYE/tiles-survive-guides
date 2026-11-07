const test=require('node:test'),assert=require('node:assert/strict'),army=require('./army-roster.js');
test('five armies sanitize malformed lists, duplicate assignments and overflow deterministically',()=>{
 const result=army.clean([{heroes:['a','a','bad','b','c','d','e','f'],mode:'Survival'},{heroes:['b','f','g'],mode:'bad'},null],['a','b','c','d','e','f','g']);
 assert.equal(result.length,5);assert.deepEqual(result[0],{heroes:['a','b','c','d','e'],mode:'Survival'});assert.deepEqual(result[1],{heroes:['f','g'],mode:'Balanced'});
 assert.deepEqual([...army.blocked(result,1)],['a','b','c','d','e']);assert.equal(army.owner(result,'g'),1);assert.equal(army.owner(result,'bad'),-1);
 assert.equal(army.index(5),0);assert.equal(army.index(-1),0);assert.equal(army.index(4),4);
 const original=JSON.stringify(result);army.clean(result,['a','b','c','d','e','f','g']);assert.equal(JSON.stringify(result),original);
});
