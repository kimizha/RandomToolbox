'use strict';
const {inspectTransaction,failureKind}=require('./transaction-read.cjs');
async function ordinaryRead(db,uid){
 const fail=category=>{const diagnosticCode=category==='TRANSACTION_UNSUPPORTED'?'READ_UNSUPPORTED':category;return {readVerified:false,diagnosticCode,stageCode:'ORDINARY_'+diagnosticCode,documentFound:null};};
 try{
  if(typeof db?.collection!=='function')return fail('READ_API_UNAVAILABLE');
  const col=db.collection('account_backups');
  if(typeof col?.doc!=='function')return fail('READ_API_MISMATCH');
  let doc=col.doc(uid);
  if(typeof doc?.field!=='function')return fail('READ_API_MISMATCH');
  doc=doc.field({_id:true,schema:true});
  if(typeof doc?.get!=='function')return fail('READ_API_MISMATCH');
  const response=await doc.get();
  if(!response||response.error||(response.code!==undefined&&response.code!==0))return fail(failureKind(response?.error||response));
  if(!Object.hasOwn(response,'data'))return fail('READ_RESULT_INVALID');
  let data=response.data;
  if(Array.isArray(data)){if(data.length>1)return fail('READ_RESULT_INVALID');data=data.length?data[0]:null;}
  if(data!==null&&(typeof data!=='object'||data._id!==uid))return fail('READ_RESULT_INVALID');
  return {readVerified:true,diagnosticCode:data===null?'DOCUMENT_ABSENT':'DOCUMENT_PRESENT',stageCode:null,documentFound:data!==null};
 }catch(error){return fail(failureKind(error));}
}
async function inspectComparison(db,uid,{deadlineMs=6000}={}){
 let control={readVerified:false,diagnosticCode:'NOT_COMPLETED',documentFound:null},phase='ORDINARY',finished=false,timer;
 const routing={requestedInstance:'SDK_DEFAULT',requestedDatabase:'SDK_DEFAULT',resolvedBackendVerified:false};
 const work=(async()=>{
  control=await ordinaryRead(db,uid);
  if(finished)return null;
  phase='TRANSACTION';
  const transaction=await inspectTransaction(db,uid);
  return {...transaction,ordinaryRead:control,transaction,routing,comparisonCode:control.readVerified?(transaction.transactionReadVerified?'BOTH_READS_VERIFIED':'ORDINARY_VERIFIED_TRANSACTION_FAILED'):(transaction.transactionReadVerified?'ORDINARY_FAILED_TRANSACTION_VERIFIED':'BOTH_UNVERIFIED')};
 })();
 try{
  return await Promise.race([work,new Promise(resolve=>{timer=setTimeout(()=>{finished=true;const transaction={transactionReadVerified:false,code:'TRANSACTION_READ_NOT_VERIFIED',phase:'UNKNOWN',diagnosticCode:'PROBE_BUDGET_EXCEEDED',stageCode:'UNKNOWN_PROBE_BUDGET_EXCEEDED'};resolve({...transaction,ordinaryRead:control,transaction,routing,comparisonCode:'PROBE_BUDGET_EXCEEDED',budgetPhase:phase});},deadlineMs);})]);
 }finally{finished=true;clearTimeout(timer);}
}
module.exports={ordinaryRead,inspectComparison};
