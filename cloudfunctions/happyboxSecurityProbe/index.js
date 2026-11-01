'use strict';
const cloudbase = require('@cloudbase/node-sdk');
const {createProbe, ENV} = require('./probe.cjs');
const app = cloudbase.init({env: ENV});
exports.main = createProbe({app, cloudContext: context => cloudbase.getCloudbaseContext(context)});
