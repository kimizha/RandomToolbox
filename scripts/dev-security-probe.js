/* HAPPYBOX_SECURITY_PROBE_TEST_ONLY */
(() => {
  'use strict';
  try { if (RandomToolboxNative.isSecurityProbeTestBuild() !== true) return; } catch (_) { return; }
  const settingsView=document.getElementById('settings');if(!settingsView)return;
  const manifest=window.hbProbeExpected,hash=/^[a-f0-9]{64}$/;
  const files=['index.js','probe.cjs','transaction-read.cjs','package.json','package-lock.json','read-control.cjs'];
  const manifestValid=manifest?.localSourceCheck==='MATCH' && manifest.revision==='readonly-comparison-v3' && hash.test(manifest.packageSha256) && files.every(n=>hash.test(manifest.files?.[n]));
  const panel=document.createElement('section');panel.className='panel';panel.id='rtDevSecurityProbe';
  panel.innerHTML='<h2>开发测试 · 只读安全核验</h2><p id="rtProbeDeployment" class="hint">线上版本尚未核实。修订标记匹配不等于线上源码摘要已核实。</p><details><summary>查看本地部署包与源码核对信息</summary><p id="rtProbeManifest" style="white-space:pre-wrap;overflow-wrap:anywhere"></p></details><label style="display:flex;gap:10px;align-items:start;margin-top:12px"><input type="checkbox" style="width:18px;height:18px;flex:0 0 18px" id="rtProbeSourceChecked"><span>我已人工核对当前线上源码与这里列出的文件摘要一致（不是按文件名或 Git 提交号判断）</span></label><button class="secondary" id="rtProbeRun" style="width:100%;margin-top:14px">使用当前真实会话核验</button><p id="rtProbeResult" role="status" style="white-space:pre-wrap;overflow-wrap:anywhere"></p>';
  settingsView.appendChild(panel);
  const run=panel.querySelector('#rtProbeRun'),output=panel.querySelector('#rtProbeResult'),deployment=panel.querySelector('#rtProbeDeployment');
  panel.querySelector('#rtProbeManifest').textContent=manifestValid?'预期修订：'+manifest.revision+'\n本地部署包 SHA-256：'+manifest.packageSha256+'\n本地源码/包内容：逐文件匹配\n'+files.map(n=>n+' SHA-256：'+manifest.files[n]).join('\n'):'本地部署包核对信息无效，禁止调用。';
  if(!manifestValid){run.disabled=true;return;}
  let busy=false;
  const uidOf=u=>String(u?.uid||u?.id||u?._id||'');
  const current=()=>window.rtLoggedIn===true&&typeof rtUser!=='undefined'?uidOf(rtUser):'';
  const known=new Set(['TRUSTED_IDENTITY_UNAVAILABLE','ENVIRONMENT_NOT_VERIFIED','REAL_USER_REQUIRED','PROBE_NOT_AUTHORIZED','TRANSACTION_API_UNAVAILABLE','TRANSACTION_READ_NOT_VERIFIED','READ_PREFLIGHT_COMPLETE']);
  const phases=new Set(['START','READ','COMMIT','COMPLETE','UNKNOWN']);
  const diagnostics=new Set(['DATABASE_INIT_FAILED','TRANSACTION_API_UNAVAILABLE','TRANSACTION_API_MISMATCH','TRANSACTION_UNSUPPORTED','PERMISSION_DENIED','DOCUMENT_PRESENT','DOCUMENT_ABSENT','DOCUMENT_NOT_FOUND_ERROR','COLLECTION_NOT_FOUND','READ_RESULT_INVALID','TRANSPORT_ERROR','UNCLASSIFIED_ERROR','CALLBACK_NOT_EXECUTED','READ_API_UNAVAILABLE','READ_API_MISMATCH','READ_UNSUPPORTED','ROUTING_TARGET_NOT_FOUND','NOT_COMPLETED','PROBE_BUDGET_EXCEEDED']);
  async function bounded(promise){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('timeout')),10000);})]);}finally{clearTimeout(timer);}}
  function display(r,uid){
    const revisionMatch=r.probeRevision===manifest.revision;
    deployment.textContent=revisionMatch?'服务端 V3 修订标记匹配；不代表数据库读取成功，也不代表线上源码摘要已远程核实。':'线上版本尚未核实：修订标记缺失或不匹配，未判定读取成功。';
    const identity=r.ok===true&&r.identityVerified===true;
    // V3 deliberately does not return UID. Never invent a client/server UID comparison.
    const trusted=identity&&revisionMatch&&r.environment==='randomtoolbox-d5gg1p6rg1d2287eb'&&(!Object.hasOwn(r,'uid')||r.uid===uid);
    const o=r.ordinaryRead&&typeof r.ordinaryRead==='object'?r.ordinaryRead:{};
    const t=r.transaction&&typeof r.transaction==='object'?r.transaction:{};
    const diagnostic=v=>diagnostics.has(v)?v:null;
    const od=diagnostic(o.diagnosticCode),td=diagnostic(t.diagnosticCode);
    const phase=phases.has(t.phase)?t.phase:null;
    const os=od&&o.stageCode==='ORDINARY_'+od?o.stageCode:null;
    const ts=td&&phase&&t.stageCode===phase+'_'+td?t.stageCode:null;
    const found=(d,v)=>(d==='DOCUMENT_PRESENT'&&v===true)||(d==='DOCUMENT_ABSENT'&&v===false);
    const ordinarySuccess=trusted&&o.readVerified===true&&found(od,o.documentFound);
    const transactionSuccess=trusted&&t.transactionReadVerified===true&&t.code==='READ_PREFLIGHT_COMPLETE'&&r.code===t.code&&r.transactionReadVerified===true&&phase==='COMPLETE'&&found(td,t.documentFound);
    const negative=d=>d&&!['DOCUMENT_PRESENT','DOCUMENT_ABSENT','NOT_COMPLETED'].includes(d);
    const ordinaryFailure=trusted&&o.readVerified===false&&negative(od)&&os;
    const transactionFailure=trusted&&t.transactionReadVerified===false&&['START','READ','COMMIT','UNKNOWN'].includes(phase)&&ts&&negative(td)&&['TRANSACTION_READ_NOT_VERIFIED','TRANSACTION_API_UNAVAILABLE'].includes(t.code)&&r.code===t.code&&r.transactionReadVerified===false;
    const state=(yes,no)=>yes?'本次成功':no?'未通过':'尚未核实（身份、版本或诊断字段缺失/不一致）';
    const presence=(yes,value)=>yes?(value?'存在':'不存在（正常空结果）'):'未知';
    let expected=null;
    if(ordinarySuccess&&transactionSuccess)expected='BOTH_READS_VERIFIED';
    else if(ordinarySuccess&&transactionFailure)expected='ORDINARY_VERIFIED_TRANSACTION_FAILED';
    else if(ordinaryFailure&&transactionSuccess)expected='ORDINARY_FAILED_TRANSACTION_VERIFIED';
    else if(ordinaryFailure&&transactionFailure)expected='BOTH_UNVERIFIED';
    const comparisons=new Set(['BOTH_READS_VERIFIED','ORDINARY_VERIFIED_TRANSACTION_FAILED','ORDINARY_FAILED_TRANSACTION_VERIFIED','BOTH_UNVERIFIED','PROBE_BUDGET_EXCEEDED','DATABASE_INIT_FAILED']);
    const budget=trusted&&r.comparisonCode==='PROBE_BUDGET_EXCEEDED'&&transactionFailure&&td==='PROBE_BUDGET_EXCEEDED';
    const summary=expected&&r.comparisonCode===expected?expected:budget?'PROBE_BUDGET_EXCEEDED':'尚未核实（结果缺失或不一致）';
    let start='未核实',read='未核实',commit='未核实';
    if(transactionSuccess){start='已完成';read='已完成';commit='已完成';}
    else if(transactionFailure&&phase==='START'){start='未通过';read='未执行';commit='未执行';}
    else if(transactionFailure&&phase==='READ'){start='已完成';read='未通过';commit='未执行';}
    else if(transactionFailure&&phase==='COMMIT'){start='已完成';read='已完成';commit='未通过';}
    output.textContent=[
      '身份验证：'+(identity?'服务端报告成功':'未获服务端确认'),
      '当前 SDK 登录会话：本次已确认（不展示 UID）',
      '可信 UID：'+(identity?'V3 服务端报告内部核对通过；不返回 UID，客户端未作逐值比对':'尚未获得服务端确认；不展示 UID'),
      '环境核对：'+(identity&&r.environment==='randomtoolbox-d5gg1p6rg1d2287eb'?'匹配':'未核实'),
      '修订标记：'+(revisionMatch?manifest.revision:'缺失或不匹配（未展示原文）'),
      '', '【普通读取】', '普通读取结果：'+state(ordinarySuccess,ordinaryFailure),
      'diagnosticCode：'+(od||'未提供或未识别'),
      'stageCode：'+(os||(ordinarySuccess?'不适用（成功）':'未提供或不一致')),
      '本人文档：'+presence(ordinarySuccess,o.documentFound),
      '', '【事务读取】', '事务读取结果：'+state(transactionSuccess,transactionFailure),
      '启动：'+start+'；读取：'+read+'；提交：'+commit,
      'phase：'+(phase||'未提供或未识别'),
      'diagnosticCode：'+(td||'未提供或未识别'),
      'stageCode：'+(ts||(transactionSuccess?'不适用（成功）':'未提供或不一致')),
      '事务结果代码：'+(known.has(t.code)?t.code:'未提供或未识别'),
      '本人文档：'+presence(transactionSuccess,t.documentFound),
      '', '对照判读：'+summary,
      '服务端 comparisonCode：'+(comparisons.has(r.comparisonCode)?r.comparisonCode:'未提供或未识别'),
      '最终结果代码：'+(known.has(r.code)?r.code:'未提供或未识别'),
      '实际数据库实例、PostgreSQL 插件、重新认证证明及设备限制：未核实'
    ].join('\n');
  }
  run.onclick=async()=>{
    if(busy)return;output.textContent='';deployment.textContent='线上版本尚未核实，等待本次调用；人工确认不会自动验证服务器。';
    if(!panel.querySelector('#rtProbeSourceChecked').checked){output.textContent='请先按本地文件摘要核对线上源码，再手动确认。确认框不授予账号权限。';return;}
    const uid=current();
    if(!uid||typeof rtAuth==='undefined'||!rtAuth||!window.rtCloudApp){output.textContent='请先使用现有登录界面登录测试账号。';return;}
    busy=true;run.disabled=true;
    try{
      const sessionResult=await bounded(rtAuth.getSession()),session=sessionResult?.data?.session;
      if(sessionResult?.error||!session||uidOf(session.user||sessionResult.data.user)!==uid||current()!==uid){output.textContent='有效会话未确认或账号已改变，请重新确认登录状态。';return;}
      const response=await bounded(window.rtCloudApp.callFunction({name:'happyboxSecurityProbe',data:{}}));
      if(current()!==uid){output.textContent='账号已切换或退出，已丢弃旧账号的核验结果。';return;}
      const r=response?.result;
      if(response?.error||!r||typeof r!=='object'||Array.isArray(r)){output.textContent='响应格式无法确认，未展示原始响应。';return;}
      display(r,uid);
    }catch(_){output.textContent=current()!==uid?'账号已改变，核验已结束。':'调用失败或超时，请检查网络、函数部署和调用权限。原始错误未输出。';}
    finally{busy=false;run.disabled=false;}
  };
})();
