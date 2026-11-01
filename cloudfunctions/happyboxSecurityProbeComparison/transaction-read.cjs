'use strict';
// Read-only transaction inspection. Never returns database content or raw provider errors.
function failureKind(error) {
  const code=typeof error?.code==='string'?error.code.toUpperCase():'';
  if (['PERMISSION_DENIED','DATABASE_PERMISSION_DENIED','UNAUTHORIZED','ACCESS_DENIED','AUTHORIZATION_FAILED'].includes(code)) return 'PERMISSION_DENIED';
  if (['NOT_SUPPORTED','UNSUPPORTED_OPERATION','TRANSACTION_NOT_SUPPORTED'].includes(code)) return 'TRANSACTION_UNSUPPORTED';
  if (['DOCUMENT_NOT_FOUND','DATABASE_DOCUMENT_NOT_EXIST'].includes(code)) return 'DOCUMENT_NOT_FOUND_ERROR';
  if (['DATABASE_NOT_FOUND','DATABASE_INSTANCE_NOT_FOUND','INSTANCE_NOT_FOUND','INVALID_DATABASE_INSTANCE'].includes(code)) return 'ROUTING_TARGET_NOT_FOUND';
  if (['COLLECTION_NOT_FOUND','DATABASE_COLLECTION_NOT_EXIST'].includes(code)) return 'COLLECTION_NOT_FOUND';
  if (['ETIMEDOUT','ECONNRESET','ENOTFOUND','NETWORK_ERROR'].includes(code)) return 'TRANSPORT_ERROR';
  return 'UNCLASSIFIED_ERROR';
}
async function inspectTransaction(db,uid) {
  let phase='START',readCompleted=false,documentFound=null;
  const fail=diagnosticCode=>({code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,diagnosticCode,phase,stageCode:phase+'_'+diagnosticCode});
  if (typeof db?.runTransaction!=='function') return {...fail('TRANSACTION_API_UNAVAILABLE'),code:'TRANSACTION_API_UNAVAILABLE'};
  try {
    await db.runTransaction(async tx=>{
      phase='READ';
      if (typeof tx?.collection!=='function') throw {code:'LOCAL_API_MISMATCH'};
      const collection=tx.collection('account_backups');
      if (typeof collection?.doc!=='function') throw {code:'LOCAL_API_MISMATCH'};
      let doc=collection.doc(uid);
      if (typeof doc?.get!=='function' || typeof doc?.field!=='function') throw {code:'LOCAL_API_MISMATCH'};
      doc=doc.field({_id:true,schema:true});
      if (typeof doc?.get!=='function') throw {code:'LOCAL_API_MISMATCH'};
      const response=await doc.get();
      if (!response || response.error || (response.code!==undefined && response.code!==0)) throw response?.error || response || {code:'LOCAL_RESULT_INVALID'};
      if (!Object.hasOwn(response,'data')) throw {code:'LOCAL_RESULT_INVALID'};
      let data=response.data;
      if (Array.isArray(data)) {
        if (data.length>1) throw {code:'LOCAL_RESULT_INVALID'};
        data=data.length?data[0]:null;
      }
      if (data===null) documentFound=false;
      else if (typeof data==='object' && data._id===uid) documentFound=true;
      else throw {code:'LOCAL_RESULT_INVALID'};
      readCompleted=true;phase='COMMIT';
    },0);
    if (!readCompleted) return fail('CALLBACK_NOT_EXECUTED');
    return {code:'READ_PREFLIGHT_COMPLETE',transactionReadVerified:true,diagnosticCode:documentFound?'DOCUMENT_PRESENT':'DOCUMENT_ABSENT',documentFound,phase:'COMPLETE'};
  } catch (error) {
    if (error?.code==='LOCAL_API_MISMATCH') return fail('TRANSACTION_API_MISMATCH');
    if (error?.code==='LOCAL_RESULT_INVALID') return fail('READ_RESULT_INVALID');
    return fail(failureKind(error));
  }
}
module.exports={inspectTransaction,failureKind};
