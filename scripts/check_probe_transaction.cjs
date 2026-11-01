'use strict';
const assert=require('node:assert/strict');
const {inspectTransaction}=require(process.argv[2] ? require('node:path').resolve(process.argv[2],'transaction-read.cjs') : './probe_transaction_candidate.cjs');
let checks=0;
async function test(name,options,expected){
 let read=0,committed=false;
 const db={runTransaction:async(fn,retries)=>{
  assert.equal(retries,0);
  if(options.startError)throw options.startError;
  if(!options.noCallback)await fn({collection:name=>{
   assert.equal(name,'account_backups');return {doc:uid=>{
    assert.equal(uid,'own');const doc={field:p=>{assert.deepEqual(p,{_id:true,schema:true});return doc;},get:async()=>{read++;if(options.readError)throw options.readError;return options.response;}};return doc;
   }};
  }});
  if(options.commitError)throw options.commitError;
  committed=true;
 }};
 const result=await inspectTransaction(options.noApi?{}:db,'own');
 for(const [k,v] of Object.entries(expected))assert.equal(result[k],v,name+': '+k);
 if(result.transactionReadVerified)assert(committed);
 assert(!JSON.stringify(result).includes('SECRET_FIXTURE'));
 assert(!JSON.stringify(result).includes('PRIVATE_PHOTO'));
 console.log('PASS',name);checks++;
}
(async()=>{
 await test('SDK transaction null is a normal absent document',{response:{data:null}},{transactionReadVerified:true,diagnosticCode:'DOCUMENT_ABSENT'});
 await test('Legacy empty list is also absent',{response:{data:[]}},{transactionReadVerified:true,documentFound:false});
 await test('Present document UID matches',{response:{data:{_id:'own',schema:2,photo:'PRIVATE_PHOTO'}}},{transactionReadVerified:true,documentFound:true});
 await test('Nonmatching UID result rejected',{response:{data:{_id:'other'}}},{transactionReadVerified:false,diagnosticCode:'READ_RESULT_INVALID'});
 for(const response of [{},{data:undefined},{data:''},{data:{}},{data:[{},{}]}])await test('Malformed data rejected '+JSON.stringify(response),{response},{transactionReadVerified:false,diagnosticCode:'READ_RESULT_INVALID'});
 await test('Missing transaction API distinguished',{noApi:true},{code:'TRANSACTION_API_UNAVAILABLE',phase:'START'});
 await test('Start permission denied',{startError:{code:'PERMISSION_DENIED',message:'SECRET_FIXTURE'}},{phase:'START',diagnosticCode:'PERMISSION_DENIED',stageCode:'START_PERMISSION_DENIED'});
 await test('Unsupported transaction start',{startError:{code:'TRANSACTION_NOT_SUPPORTED'}},{phase:'START',diagnosticCode:'TRANSACTION_UNSUPPORTED'});
 await test('Read permission denied',{readError:{code:'PERMISSION_DENIED'}},{phase:'READ',diagnosticCode:'PERMISSION_DENIED',stageCode:'READ_PERMISSION_DENIED'});
 await test('Thrown missing document is not confirmed successful commit',{readError:{code:'DOCUMENT_NOT_FOUND'}},{phase:'READ',transactionReadVerified:false,diagnosticCode:'DOCUMENT_NOT_FOUND_ERROR'});
 await test('Returned error distinguished',{response:{error:{code:'PERMISSION_DENIED'}}},{phase:'READ',diagnosticCode:'PERMISSION_DENIED',stageCode:'READ_PERMISSION_DENIED'});
 await test('Null read then commit failure is not success',{response:{data:null},commitError:{code:'ETIMEDOUT'}},{phase:'COMMIT',transactionReadVerified:false,diagnosticCode:'TRANSPORT_ERROR',stageCode:'COMMIT_TRANSPORT_ERROR'});
 await test('Unknown exception does not leak raw details',{readError:Error('SECRET_FIXTURE')},{diagnosticCode:'UNCLASSIFIED_ERROR'});
 await test('No callback cannot fabricate success',{noCallback:true},{transactionReadVerified:false,diagnosticCode:'CALLBACK_NOT_EXECUTED'});
 await test('Commit permission separately classified',{response:{data:null},commitError:{code:'PERMISSION_DENIED'}},{phase:'COMMIT',stageCode:'COMMIT_PERMISSION_DENIED',transactionReadVerified:false});
 await test('Missing collection distinguished',{readError:{code:'COLLECTION_NOT_FOUND'}},{diagnosticCode:'COLLECTION_NOT_FOUND',phase:'READ'});
 console.log(`${checks} offline integrated transaction scenarios passed. No CloudBase calls or writes.`);
})().catch(e=>{console.error(e);process.exitCode=1});
