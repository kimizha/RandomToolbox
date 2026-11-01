'use strict';

// Preflight only. No application login admission, token decoding or database writes.
const {inspectTransaction}=require('./transaction-read.cjs');
const REVISION='readonly-tx-null-v2';
const ENV = 'randomtoolbox-d5gg1p6rg1d2287eb';
function createProbe({app, cloudContext, allowedUids = []}) {
  const allowed = new Set(Array.isArray(allowedUids) && allowedUids.length <= 10 &&
    allowedUids.every(uid => typeof uid === 'string' && uid.length > 0 && uid.length <= 256) ? allowedUids : []);
  const handler = async function probe(_event, context) {
    let identity, runtime, user;
    try {
      runtime = cloudContext(context);
      identity = await app.auth().getAuthContext(context);
      user = app.auth().getUserInfo();
    } catch (_) {
      return {ok: false, code: 'TRUSTED_IDENTITY_UNAVAILABLE'};
    }
    if (!runtime || runtime.TCB_ENV !== ENV) return {ok: false, code: 'ENVIRONMENT_NOT_VERIFIED'};
    const uid = identity && identity.uid;
    if (typeof uid !== 'string' || !uid || uid.length > 256 ||
        runtime.TCB_UUID !== uid || !user || user.uid !== uid ||
        user.isAnonymous !== false) {
      return {ok: false, code: 'REAL_USER_REQUIRED'};
    }
    if (!allowed.has(uid)) return {ok: false, code: 'PROBE_NOT_AUTHORIZED'};
    const result = {
      ok: true,
      identityVerified: true,
      // Returned only to this authenticated caller; never log context or credentials.
      uid,
      environment: ENV,
      transactionReadVerified: false,
      concurrentWritesVerified: false,
      freshReauthenticationVerified: false,
      perDeviceProviderRevocationVerified: false
    };
    let db;
    try { db=app.database(); }
    catch (_) { return {...result,code:'TRANSACTION_READ_NOT_VERIFIED',diagnosticCode:'DATABASE_INIT_FAILED',phase:'START',stageCode:'START_DATABASE_INIT_FAILED'}; }
    return {...result,...await inspectTransaction(db,uid)};
  };
  return async (event,context)=>({...await handler(event,context),probeRevision:REVISION});
}
module.exports = {createProbe, ENV, REVISION};
