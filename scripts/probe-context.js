/* HAPPYBOX_SECURITY_PROBE_TEST_ONLY: actual instances captured at SDK initialization. */
(() => {
 'use strict';
 let context=null;
 const uidOf=user=>String(user?.uid||user?.id||user?._id||'');
 const error=code=>Object.assign(new Error(code),{code});
 const missing=new Set(['FUNCTION_NOT_FOUND','FUNCTION_NOT_EXIST','FUNCTION_NOT_EXISTS','RESOURCENOTFOUND.FUNCTIONNAME','RESOURCENOTFOUND.FUNCTION']);
 function callError(value){return error(missing.has(String(value?.code||value?.errorCode||'').toUpperCase())?'PROBE_FUNCTION_NOT_FOUND':'PROBE_CALL_FAILED')}
 window.hbAttachProbeContext=({app,auth,currentUser,syncPaused})=>{context={app,auth,currentUser,syncPaused}};
 window.hbReadOnlyProbeContext={
  ready:()=>!!context&&typeof context.auth?.getSession==='function'&&typeof context.app?.callFunction==='function',
  async execute(sessionConfirmed){
   const own=context;
   if(!own||typeof own.auth?.getSession!=='function'||typeof own.app?.callFunction!=='function')throw error('SDK_NOT_READY');
   if(own.syncPaused()!==true)throw error('SYNC_NOT_PAUSED');
   let before;
   try{before=await own.auth.getSession()}catch(_){throw error('SESSION_CHECK_FAILED')}
   if(before?.error)throw error('SESSION_CHECK_FAILED');
   const session=before?.data?.session,uid=uidOf(session?.user||before?.data?.user);
   if(!session||!uid||uid.length>256)throw error('SESSION_REQUIRED');
   if(context!==own||uidOf(own.currentUser())!==uid)throw error('ACCOUNT_CHANGED');
   sessionConfirmed();
   let response;
   try{response=await own.app.callFunction({name:'happyboxSecurityProbe',data:{}})}catch(e){throw callError(e)}
   if(response?.error)throw callError(response.error);
   if(missing.has(String(response?.code||'').toUpperCase()))throw callError(response);
   let after;
   try{after=await own.auth.getSession()}catch(_){throw error('SESSION_CHECK_FAILED')}
   if(after?.error)throw error('SESSION_CHECK_FAILED');
   const next=after?.data?.session;
   if(context!==own||!next||uidOf(next.user||after?.data?.user)!==uid||uidOf(own.currentUser())!==uid)throw error('ACCOUNT_CHANGED');
   if(own.syncPaused()!==true)throw error('SYNC_NOT_PAUSED');
   const result=response?.result;
   if(!result||typeof result!=='object'||Array.isArray(result))throw error('PROBE_RESPONSE_INVALID');
   return {result,expectedUid:uid};
  }
 };
})();
