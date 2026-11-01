'use strict';
// Source contract check only: never initialize SDK, credentials, transport or cloud services.
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),vm=require('node:vm');
if(!process.argv[2])throw Error('Pass directory containing locked probe node_modules');
const root=path.resolve(process.argv[2]);
const read=p=>fs.readFileSync(path.join(root,'node_modules',p),'utf8');
assert.equal(JSON.parse(read('@cloudbase/node-sdk/package.json')).version,'4.2.1');
const source=read('@cloudbase/js-sdk/database/dist/index.js');
const match=source.match(/this\._transactionId\?\[2,\{data:([^,}]+),requestId:/);
assert(match,'Review changed SDK result contract');
const variable=match[1].match(/^([A-Za-z_$][\w$]*)\[0\]\|\|null$/);assert(variable);
const empty=vm.runInNewContext(match[1],{[variable[1]]:[]});assert.equal(empty,null);
assert(source.includes('function _e(t,e)')&&source.includes('t(n)')&&source.includes('n.commit()'));
console.log('Pinned SDK source contract: transaction doc.get empty result becomes data=null.');
const {createProbe,ENV}=require('../cloudfunctions/happyboxSecurityProbe/probe.cjs');
const {inspectTransaction}=require('./probe_transaction_candidate.cjs');
const db={runTransaction:async fn=>fn({collection:name=>{
 assert.equal(name,'account_backups');return {doc:uid=>{
  assert.equal(uid,'own');const doc={field:()=>doc,get:async()=>({data:empty})};return doc;
 }};
}})};
(async()=>{
 const old=createProbe({app:{auth:()=>({getAuthContext:async()=>({uid:'own'}),getUserInfo:()=>({uid:'own',isAnonymous:false})}),database:()=>db},cloudContext:()=>({TCB_ENV:ENV,TCB_UUID:'own'}),allowedUids:['own']});
 const before=await old({},{});assert.equal(before.code,'READ_PREFLIGHT_COMPLETE');assert.equal(before.documentFound,false);
 const after=await inspectTransaction(db,'own');assert.equal(after.transactionReadVerified,true);assert.equal(after.documentFound,false);
 console.log('Integrated probe accepts SDK empty shape after transaction success.');
 console.log('SDK source-contract and isolated reproduction passed; not real-cloud integration.');
})().catch(e=>{console.error(e);process.exitCode=1});
