'use strict';
const assert=require('node:assert/strict');
const {createProbe,ENV}=require('../cloudfunctions/happyboxSecurityProbeComparison/probe.cjs');
const {inspectComparison}=require('../cloudfunctions/happyboxSecurityProbeComparison/read-control.cjs');
let count=0;
function database(options={}){
 let ordinary=0,transaction=0,initializations=0;
 const collection=(lane)=>name=>{
  assert.equal(name,'account_backups');
  return {doc:uid=>{
   assert.equal(uid,'own');const doc={field:p=>{assert.deepEqual(p,{_id:true,schema:true});return doc;},get:async()=>{
    if(lane==='ordinary')ordinary++;else transaction++;
    if(options.hangOrdinary&&lane==='ordinary')return new Promise(()=>{});
    if(options[lane+'Error'])throw options[lane+'Error'];
    return options[lane+'Response']||{data:{_id:'own',schema:2,photo:'PRIVATE_BACKUP_FIXTURE'}};
   }};return doc;
  }};
 };
 const db={collection:collection('ordinary'),runTransaction:async(fn,retries)=>{
  initializations++;assert.equal(retries,0);
  if(options.startError)throw options.startError;
  if(options.hangTransaction)return new Promise(()=>{});
  await fn({collection:collection('transaction')});
  if(options.commitError)throw options.commitError;
 }};
 return {db,stats:()=>({ordinary,transaction,initializations})};
}
async function check(name,options,test){
 const {db,stats}=database(options);const r=await inspectComparison(db,'own',{deadlineMs:options.deadlineMs||200});
 test(r,stats());assert(!JSON.stringify(r).includes('PRIVATE_BACKUP_FIXTURE'));assert(!JSON.stringify(r).includes('SECRET_FIXTURE'));
 assert.equal(r.routing.resolvedBackendVerified,false);console.log('PASS',name);count++;
}
(async()=>{
 await check('Same db, same UID, both read successfully',{},(r,s)=>{assert.equal(r.comparisonCode,'BOTH_READS_VERIFIED');assert.deepEqual(s,{ordinary:1,transaction:1,initializations:1});});
 await check('Both empty results are normal',{ordinaryResponse:{data:[]},transactionResponse:{data:null}},r=>{assert.equal(r.ordinaryRead.documentFound,false);assert.equal(r.transaction.documentFound,false);assert.equal(r.comparisonCode,'BOTH_READS_VERIFIED');});
 await check('Actual reported start failure kept distinct',{startError:{code:'COLLECTION_NOT_FOUND',message:'SECRET_FIXTURE'}},(r,s)=>{assert.equal(r.ordinaryRead.readVerified,true);assert.equal(r.transaction.stageCode,'START_COLLECTION_NOT_FOUND');assert.equal(s.transaction,0);assert.equal(r.comparisonCode,'ORDINARY_VERIFIED_TRANSACTION_FAILED');});
 for(const code of ['PERMISSION_DENIED','DATABASE_NOT_FOUND','COLLECTION_NOT_FOUND','NOT_SUPPORTED','OTHER']){
  await check('Ordinary error does not skip transaction: '+code,{ordinaryError:{code,message:'SECRET_FIXTURE'}},r=>{assert.equal(r.ordinaryRead.readVerified,false);assert.equal(r.transactionReadVerified,true);assert.equal(r.comparisonCode,'ORDINARY_FAILED_TRANSACTION_VERIFIED');});
 }
 await check('Explicit route error categorized',{ordinaryError:{code:'INSTANCE_NOT_FOUND'},startError:{code:'DATABASE_NOT_FOUND'}},r=>{assert.equal(r.ordinaryRead.diagnosticCode,'ROUTING_TARGET_NOT_FOUND');assert.equal(r.transaction.diagnosticCode,'ROUTING_TARGET_NOT_FOUND');});
 await check('Both missing collection is not fabricated success',{ordinaryError:{code:'COLLECTION_NOT_FOUND'},startError:{code:'COLLECTION_NOT_FOUND'}},r=>assert.equal(r.comparisonCode,'BOTH_UNVERIFIED'));
 await check('Commit refusal not successful',{commitError:{code:'PERMISSION_DENIED'}},r=>assert.equal(r.transaction.stageCode,'COMMIT_PERMISSION_DENIED'));
 await check('Other UID returned cannot pass',{ordinaryResponse:{data:{_id:'victim'}}},r=>assert.equal(r.ordinaryRead.diagnosticCode,'READ_RESULT_INVALID'));
 await check('Ordinary returned error classified',{ordinaryResponse:{error:{code:'PERMISSION_DENIED'}}},r=>assert.equal(r.ordinaryRead.diagnosticCode,'PERMISSION_DENIED'));
 await check('Ordinary malformed data not success',{ordinaryResponse:{}},r=>assert.equal(r.ordinaryRead.diagnosticCode,'READ_RESULT_INVALID'));
 await check('Hanging ordinary read prevents later transaction',{hangOrdinary:true,deadlineMs:15},(r,s)=>{assert.equal(r.comparisonCode,'PROBE_BUDGET_EXCEEDED');assert.equal(r.budgetPhase,'ORDINARY');assert.equal(s.initializations,0);});
 await check('Hanging transaction retains ordinary result',{hangTransaction:true,deadlineMs:15},r=>{assert.equal(r.ordinaryRead.readVerified,true);assert.equal(r.transactionReadVerified,false);assert.equal(r.budgetPhase,'TRANSACTION');});
 let calls=0;const {db}=database({startError:{code:'COLLECTION_NOT_FOUND'}});
 const probe=createProbe({app:{auth:()=>({getAuthContext:async()=>({uid:'own'}),getUserInfo:()=>({uid:'own',isAnonymous:false})}),database:()=>{calls++;return db;}},cloudContext:()=>({TCB_ENV:ENV,TCB_UUID:'own'}),allowedUids:['own']});
 const out=await probe({uid:'victim',instance:'other',database:'other'},{});assert.equal(calls,1);assert.equal(out.probeRevision,'readonly-comparison-v3');assert.equal(out.ordinaryRead.readVerified,true);assert.equal(out.transaction.phase,'START');assert(!Object.hasOwn(out,'uid'));assert(!JSON.stringify(out).includes('victim'));count++;
 console.log(`${count} offline comparison scenarios passed; no CloudBase calls or data writes.`);
})().catch(e=>{console.error(e);process.exitCode=1});
