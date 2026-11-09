'use strict';
// Regression: locked SDK, blocked network and actual production modules.
// Usage: node scripts/check_probe_document_absence.cjs locked-dependency-directory
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let external=0;
const blocked=()=>{external++;throw Error('NETWORK_BLOCKED')};
global.fetch=blocked;
for(const name of ['http','https']){require(name).request=blocked;require(name).get=blocked}
require('net').connect=blocked;require('net').createConnection=blocked;
const deps=path.resolve(process.argv[2] || '');
assert(process.argv[2], 'Pass the locked deployment dependency directory');
const sdk=require(path.join(deps,'node_modules/@cloudbase/js-sdk/database/dist/index.js'));
assert.equal(require(path.join(deps,'node_modules/@cloudbase/node-sdk/package.json')).version,'4.2.1');
assert.equal(require(path.join(deps,'node_modules/@cloudbase/js-sdk/package.json')).version,'3.10.4');
let component;sdk.registerDatabase({registerComponent:value=>component=value});
const root=path.resolve(__dirname,'../cloudfunctions/happyboxSecurityProbeComparison');
const baseline=require('node:os').tmpdir()+'/happybox-probe-baseline-';
const oldRoot=fs.mkdtempSync(baseline);
const rollback=path.resolve(__dirname,'../deployment/security-probe/HappyboxSecurityProbe-readonly-comparison-v3-rollback.zip');
const archive=fs.readFileSync(rollback);
assert.equal(require('node:crypto').createHash('sha256').update(archive).digest('hex'),'90a7958152e8372deea9d49a5a481a50029bb52e6616a622a5916efaf86b6d44');
const extraction=require('node:child_process').spawnSync('python3',['-c',"import sys,zipfile;from pathlib import Path;z=zipfile.ZipFile(sys.argv[1]);out=Path(sys.argv[2]);[(out/f).write_bytes(z.read(f)) for f in ('probe.cjs','transaction-read.cjs','read-control.cjs')]",rollback,oldRoot],{encoding:'utf8'});
assert.equal(extraction.status,0,'Cannot extract immutable baseline');
process.on('exit',()=>fs.rmSync(oldRoot,{recursive:true,force:true}));
function load(folder){
 const cache={};
 function read(name){if(cache[name])return cache[name];const file=path.join(folder,name);const source=fs.readFileSync(file,'utf8');const module={exports:{}};cache[name]=module.exports;vm.runInNewContext(source,{module,exports:module.exports,require:name=>read(path.basename(name)),Object,Set,Array,Promise,Error,setTimeout,clearTimeout},{filename:name});cache[name]=module.exports;return module.exports}
 return {ordinary:read('read-control.cjs').ordinaryRead,transaction:read('transaction-read.cjs').inspectTransaction,create:read('probe.cjs').createProbe};
}
const old=load(oldRoot),candidate=load(root);
let checks=0;
function check(name,test){test();checks++;console.log('PASS '+name)}
function database({readCode='DOCUMENT_NOT_FOUND',startCode,commitCode,readStatus=404}={}){
 const calls=[];
 function Request(config){this.config=config}
 Request.prototype.send=()=>{throw Error('Legacy routing forbidden')};
 Request.prototype.gateWay=async function(options){
  const url=options.url;calls.push({method:options.method,url});
  if(url.endsWith('/transactions'))return startCode?{statusCode:404,data:{code:startCode}}:{statusCode:201,data:{transactionId:'fixture-tx'}};
  if(url.endsWith('/commit'))return commitCode?{statusCode:503,data:{code:commitCode}}:{statusCode:204,data:''};
  if(url.endsWith('/rollback'))return {statusCode:204,data:''};
  assert.equal(options.method,'GET');assert(url.includes('/collections/account_backups/documents/fixture-own?'));assert(url.includes('projection='));
  return {statusCode:readStatus,data:readCode?{code:readCode,message:'PRIVATE_FIXTURE'}:{_id:'fixture-own',schema:2}};
 };
 const app={config:{endPointMode:'GATEWAY'},platform:{adapter:{},runtime:'node'},request:new Request({})};
 return {db:component.entity.database.call(app),calls};
}
(async()=>{
 let x=database(),r=await old.ordinary(x.db,'fixture-own');
 check('Original ordinary read classifies SDK missing exception as failure',()=>{assert.equal(r.readVerified,false);assert.equal(r.diagnosticCode,'DOCUMENT_NOT_FOUND_ERROR')});
 x=database();r=await old.transaction(x.db,'fixture-own');
 check('Original actual SDK transaction starts, missing read fails and rolls back',()=>{assert.equal(r.phase,'READ');assert.equal(r.transactionReadVerified,false);assert(x.calls.some(x=>x.url.endsWith('/transactions')));assert(x.calls.some(x=>x.url.endsWith('/rollback')));assert(!x.calls.some(x=>x.url.endsWith('/commit')))});
 x=database();r=await candidate.ordinary(x.db,'fixture-own');
 check('Candidate normalizes canonical missing GET to absence',()=>{assert.equal(r.readVerified,true);assert.equal(r.diagnosticCode,'DOCUMENT_ABSENT');assert.equal(r.documentFound,false)});
 x=database();r=await candidate.transaction(x.db,'fixture-own');
 check('Candidate succeeds only after actual SDK commit path returns successfully',()=>{assert.equal(r.transactionReadVerified,true);assert.equal(r.phase,'COMPLETE');assert.equal(r.diagnosticCode,'DOCUMENT_ABSENT');assert(x.calls.some(x=>x.url.endsWith('/commit')));assert(!x.calls.some(x=>x.url.endsWith('/rollback')))});
 for(const code of ['DATABASE_PERMISSION_DENIED','DATABASE_COLLECTION_NOT_EXIST','DATABASE_NOT_FOUND','NETWORK_ERROR','DATABASE_TIMEOUT','DATABASE_TRANSACTION_CONFLICT','DATABASE_DOCUMENT_NOT_EXIST','OTHER_ERROR']){
  x=database({readCode:code});r=await candidate.ordinary(x.db,'fixture-own');
  check(code+' ordinary error is not successful absence',()=>assert.equal(r.readVerified,false));
  x=database({readCode:code});r=await candidate.transaction(x.db,'fixture-own');
  check(code+' transaction READ remains failed, commit is not called',()=>{assert.equal(r.transactionReadVerified,false);assert.equal(r.phase,'READ');assert(!x.calls.some(x=>x.url.endsWith('/commit')))});
 }
 for(const [phase,options] of [['START',{startCode:'DOCUMENT_NOT_FOUND'}],['COMMIT',{commitCode:'DOCUMENT_NOT_FOUND'}],['COMMIT',{commitCode:'DATABASE_TRANSACTION_FAIL'}]]){
  x=database(options);r=await candidate.transaction(x.db,'fixture-own');
  check(phase+' error never normalized as missing document',()=>{assert.equal(r.transactionReadVerified,false);assert.equal(r.phase,phase)});
 }
 const returned=values=>({collection:()=>({doc:()=>({field(){return this},get:async()=>values})})});
 for(const value of [{code:'DOCUMENT_NOT_FOUND'},{error:{code:'DOCUMENT_NOT_FOUND'}}]){
  r=await candidate.ordinary(returned(value),'fixture-own');check('Returned canonical error also normalizes',()=>{assert.equal(r.readVerified,true);assert.equal(r.diagnosticCode,'DOCUMENT_ABSENT')});
 }
 for(const value of [{error:{code:'DOCUMENT_NOT_FOUND',statusCode:403}},{code:'DATABASE_PERMISSION_DENIED',error:{code:'DOCUMENT_NOT_FOUND'}},{code:404},{error:{code:'DATABASE_PERMISSION_DENIED',message:'DOCUMENT_NOT_FOUND'}},{error:{code:'DOCUMENT_NOT_FOUND',status:500}}]){
  r=await candidate.ordinary(returned(value),'fixture-own');check('Contradictory status, generic 404 or permission message cannot become absence',()=>assert.equal(r.readVerified,false));
 }
 for(const data of [[],null]){r=await candidate.ordinary(returned({data}),'fixture-own');check('Existing valid empty-data behavior preserved',()=>assert.equal(r.readVerified,true))}
 for(const [name,identity,runtime,allowed] of [['anonymous',{uid:'fixture-own',isAnonymous:true},'correct',['fixture-own']],['wrong environment',{uid:'fixture-own',isAnonymous:false},'wrong',['fixture-own']],['not allowed',{uid:'fixture-own',isAnonymous:false},'correct',[]]]){
  let dbCalls=0;const env='randomtoolbox-d5gg1p6rg1d2287eb';
  const probe=candidate.create({app:{auth:()=>({getAuthContext:async()=>({uid:'fixture-own'}),getUserInfo:()=>identity}),database:()=>{dbCalls++;throw Error('must not read')}},cloudContext:()=>({TCB_ENV:runtime==='correct'?env:'other',TCB_UUID:'fixture-own'}),allowedUids:allowed});
  r=await probe({uid:'forged',role:'admin'},{});check(name+' still rejected before database access',()=>{assert.equal(r.ok,false);assert.equal(dbCalls,0)});
 }
 x=database();const env='randomtoolbox-d5gg1p6rg1d2287eb';const probe=candidate.create({app:{auth:()=>({getAuthContext:async()=>({uid:'fixture-own'}),getUserInfo:()=>({uid:'fixture-own',isAnonymous:false})}),database:()=>x.db},cloudContext:()=>({TCB_ENV:env,TCB_UUID:'fixture-own'}),allowedUids:['fixture-own']});r=await probe({},{});
 check('Patched candidate preserves V3 result contract and no private payload escapes',()=>{assert.equal(r.comparisonCode,'BOTH_READS_VERIFIED');assert.equal(r.code,'READ_PREFLIGHT_COMPLETE');assert(!JSON.stringify(r).includes('PRIVATE_FIXTURE'))});
 check('External network requests',()=>assert.equal(external,0));
 console.log(checks+' offline production regression checks passed; actual locked SDK with mocked gateway, no Tencent Cloud access.');
})().catch(error=>{console.error('Offline review failed:',error.code||error.name);process.exitCode=1});
