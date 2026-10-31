const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('app/src/main/assets/ui/game-library.js','utf8'),ctx);
const lib=JSON.parse(JSON.stringify(ctx.window.RT_GAME_LIBRARY));
for(const [key,min] of [['truth',200],['dare',160],['spy',400],['soups',100]])assert.ok(lib[key].length>=min,key+' expanded');
for(const key of ['truth','dare']){assert.equal(new Set(lib[key]).size,lib[key].length);assert.ok(lib[key].every(text=>typeof text==='string'&&text.trim().length>=5))}
assert.equal(new Set([...lib.truth,...lib.dare]).size,lib.truth.length+lib.dare.length);
const pairs=lib.spy.map(pair=>{assert.equal(pair.length,2);assert.ok(pair.every(word=>typeof word==='string'&&word.trim()));assert.notEqual(pair[0],pair[1]);return [...pair].sort().join('|')});assert.equal(new Set(pairs).size,pairs.length);
assert.equal(new Set(lib.soups.map(s=>s.id)).size,lib.soups.length);assert.equal(new Set(lib.soups.map(s=>s.title)).size,lib.soups.length);
for(const s of lib.soups){assert.equal(s.types.length,2);assert.ok(['white','red','black','spicy'].includes(s.types[0]));assert.ok(['realistic','supernatural'].includes(s.types[1]));assert.match(s.id,/^soup-\d+$/);assert.ok(['easy','medium','hard'].includes(s.difficulty));assert.ok(s.surface.length>=30);assert.ok(s.solution.length>=45);assert.equal(s.hints.length,3);assert.equal(s.facts.length,3);assert.equal(new Set(s.hints).size,3);assert.ok([...s.hints,...s.facts].every(x=>typeof x==='string'&&x.length>=4))}
for(const level of ['easy','medium','hard'])assert.ok(lib.soups.filter(s=>s.difficulty===level).length>=8);
for(const type of ['white','red','black','spicy','realistic','supernatural'])assert.ok(lib.soups.filter(s=>s.types.includes(type)).length>=6,'Type coverage: '+type);
console.log(JSON.stringify({truth:lib.truth.length,dare:lib.dare.length,spy:lib.spy.length,soups:lib.soups.length,levels:Object.fromEntries(['easy','medium','hard'].map(l=>[l,lib.soups.filter(s=>s.difficulty===l).length]))}));
console.log('Curated library validation passed; no external content or cloud calls.');
