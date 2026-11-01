'use strict';

// Preflight only. No application login admission, token decoding or database writes.
const ENV = 'randomtoolbox-d5gg1p6rg1d2287eb';
function createProbe({app, cloudContext, allowedUids = []}) {
  const allowed = new Set(Array.isArray(allowedUids) && allowedUids.length <= 10 &&
    allowedUids.every(uid => typeof uid === 'string' && uid.length > 0 && uid.length <= 256) ? allowedUids : []);
  return async function probe(_event, context) {
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
    try {
      const db = app.database();
      if (typeof db.runTransaction !== 'function') return {...result, code: 'TRANSACTION_API_UNAVAILABLE'};
      await db.runTransaction(async tx => {
        // Read own existing document only. The contents never leave the function.
        const response = await tx.collection('account_backups').doc(uid).get();
        if (!response || response.error || (response.code !== undefined && response.code !== 0) ||
            !Object.hasOwn(response, 'data') || response.data === null || typeof response.data !== 'object') {
          throw new Error('Read response not verified');
        }
      });
      return {...result, transactionReadVerified: true, code: 'READ_PREFLIGHT_COMPLETE'};
    } catch (_) {
      // May be absent backup, IAM, network or unsupported transaction. No false success.
      return {...result, code: 'TRANSACTION_READ_NOT_VERIFIED'};
    }
  };
}
module.exports = {createProbe, ENV};
