'use strict';
const cloudbase = require('@cloudbase/node-sdk');
const {createProbe, ENV} = require('./probe.cjs');
const app = cloudbase.init({env: ENV, timeout: 3000});
let allowedUids = [];
try { allowedUids = JSON.parse(process.env.HAPPYBOX_PROBE_ALLOWED_UIDS || '[]'); } catch (_) {}
exports.main = createProbe({app, cloudContext: context => cloudbase.getCloudbaseContext(context), allowedUids});
