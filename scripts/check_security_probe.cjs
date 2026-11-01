'use strict';
const assert = require('node:assert/strict');
const {createProbe, ENV} = require('../cloudfunctions/happyboxSecurityProbe/probe.cjs');
let count = 0;
async function scenario(name, change, expected, reads = 0) {
  let actualReads = 0;
  const source = {uid: 'own-user', anonymous: false, env: ENV, runtimeUid: 'own-user', userUid: 'own-user'};
  const app = {
    auth: () => ({getAuthContext: async () => ({uid: source.uid}), getUserInfo: () => ({uid: source.userUid, isAnonymous: source.anonymous})}),
    database: () => ({runTransaction: async fn => fn({collection: name => {
      assert.equal(name, 'account_backups');
      return {doc: uid => {
        assert.equal(uid, 'own-user');
        const doc={field:p=>{assert.deepEqual(p,{_id:true,schema:true});return doc;},get: async () => {actualReads++; if (source.failRead) throw Error('private server diagnostic'); return source.response || {data: {_id:'own-user',schema:2,photo:'private-photo'}};}};return doc;
      }};
    }})})
  };
  change(source, app);
  const probe = createProbe({app, allowedUids: source.allowedUids === undefined ? ['own-user'] : source.allowedUids, cloudContext: context => {
    assert.equal(context, 'runtime-context');
    return {TCB_ENV: source.env, TCB_UUID: source.runtimeUid};
  }});
  // Malicious event properties must never override platform identity or environment.
  const out = await probe({uid: 'victim', context: {TCB_UUID: 'victim'}, env: 'other', role: 'admin', explicitLogin: true}, 'runtime-context');
  assert.equal(out.probeRevision,'readonly-tx-null-v2');
  assert.equal(out.code, expected);assert.equal(actualReads, reads);
  const encoded = JSON.stringify(out);assert(!encoded.includes('private-photo'));assert(!encoded.includes('private server diagnostic'));
  assert(!encoded.includes('victim'));assert.notEqual(out.freshReauthenticationVerified, true);
  assert.notEqual(out.concurrentWritesVerified, true);assert.notEqual(out.perDeviceProviderRevocationVerified, true);
  console.log('PASS', name); count++;
}
(async () => {
  await scenario('Own trusted identity; own transaction read only', () => {}, 'READ_PREFLIGHT_COMPLETE', 1);
  await scenario('Normal null document succeeds', s=>{s.response={data:null};},'READ_PREFLIGHT_COMPLETE',1);
  await scenario('Mismatched document UID is rejected', s=>{s.response={data:{_id:'other'}};},'TRANSACTION_READ_NOT_VERIFIED',1);
  await scenario('Missing identity denied', s => {s.uid = '';}, 'REAL_USER_REQUIRED');
  await scenario('Anonymous identity denied', s => {s.anonymous = true;}, 'REAL_USER_REQUIRED');
  await scenario('Missing anonymous classification denied', s => {delete s.anonymous;}, 'REAL_USER_REQUIRED');
  await scenario('Conflicting runtime identity denied', s => {s.runtimeUid = 'other';}, 'REAL_USER_REQUIRED');
  await scenario('Conflicting user identity denied', s => {s.userUid = 'other';}, 'REAL_USER_REQUIRED');
  await scenario('Other environment denied', s => {s.env = 'other';}, 'ENVIRONMENT_NOT_VERIFIED');
  await scenario('Missing environment denied', s => {delete s.env;}, 'ENVIRONMENT_NOT_VERIFIED');
  await scenario('Provider identity failure fails closed', (_, app) => {app.auth = () => {throw Error('private server diagnostic');};}, 'TRUSTED_IDENTITY_UNAVAILABLE');
  await scenario('No transaction method reported accurately', (_, app) => {app.database = () => ({});}, 'TRANSACTION_API_UNAVAILABLE');
  await scenario('Failed read not presented as success', s => {s.failRead = true;}, 'TRANSACTION_READ_NOT_VERIFIED', 1);
  await scenario('Empty server allowlist denies database access', s => {s.allowedUids = [];}, 'PROBE_NOT_AUTHORIZED');
  await scenario('Other tester UID denies database access', s => {s.allowedUids = ['other'];}, 'PROBE_NOT_AUTHORIZED');
  await scenario('Malformed server allowlist fails closed', s => {s.allowedUids = 'own-user';}, 'PROBE_NOT_AUTHORIZED');
  await scenario('Oversized server allowlist fails closed', s => {s.allowedUids = Array(11).fill('own-user');}, 'PROBE_NOT_AUTHORIZED');
  await scenario('Returned read error is not success', s => {s.response = {error: {message: 'private server diagnostic'}};}, 'TRANSACTION_READ_NOT_VERIFIED', 1);
  await scenario('Returned error code is not success', s => {s.response = {code: 'DENIED', data: {}};}, 'TRANSACTION_READ_NOT_VERIFIED', 1);
  await scenario('Missing response data is not success', s => {s.response = {};}, 'TRANSACTION_READ_NOT_VERIFIED', 1);
  await scenario('Empty result can verify a read, not backup existence', s => {s.response = {data: []};}, 'READ_PREFLIGHT_COMPLETE', 1);
  console.log(`${count} offline security preflight scenarios passed; no CloudBase connection.`);
})().catch(e => {console.error(e);process.exitCode = 1;});
