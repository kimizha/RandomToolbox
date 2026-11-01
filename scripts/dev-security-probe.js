/* HAPPYBOX_SECURITY_PROBE_TEST_ONLY */
(() => {
  'use strict';
  try { if (RandomToolboxNative.isSecurityProbeTestBuild() !== true) return; } catch (_) { return; }
  const settingsView=document.getElementById('settings');if(!settingsView)return;
  const manifest=window.hbProbeExpected,hash=/^[a-f0-9]{64}$/;
  const files=['index.js','probe.cjs','transaction-read.cjs','package.json','package-lock.json'];
  const manifestValid=manifest?.localSourceCheck==='MATCH' && manifest.revision==='readonly-tx-null-v2' && hash.test(manifest.packageSha256) && files.every(n=>hash.test(manifest.files?.[n]));
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
  const phases=new Set(['START','READ','COMMIT','COMPLETE']);
  const diagnostics=new Set(['DATABASE_INIT_FAILED','TRANSACTION_API_UNAVAILABLE','TRANSACTION_API_MISMATCH','TRANSACTION_UNSUPPORTED','PERMISSION_DENIED','DOCUMENT_PRESENT','DOCUMENT_ABSENT','DOCUMENT_NOT_FOUND_ERROR','COLLECTION_NOT_FOUND','READ_RESULT_INVALID','TRANSPORT_ERROR','UNCLASSIFIED_ERROR','CALLBACK_NOT_EXECUTED']);
  async function bounded(promise){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('timeout')),10000);})]);}finally{clearTimeout(timer);}}
  function display(r,uid){
    const revisionMatch=r.probeRevision===manifest.revision;
    deployment.textContent=revisionMatch?'服务端修订标记匹配；线上源码摘要未由客户端远程核实。确认框仅记录人工核对。':'线上版本尚未核实：服务端修订标记缺失或不匹配。请核对实际部署代码，未自动判为成功。';
    const identity=r.ok===true&&r.identityVerified===true;
    const same=identity&&r.uid===uid&&r.environment==='randomtoolbox-d5gg1p6rg1d2287eb';
    const phase=phases.has(r.phase)?r.phase:null;
    const diagnostic=diagnostics.has(r.diagnosticCode)?r.diagnosticCode:null;
    const stage=phase&&diagnostic&&r.stageCode===phase+'_'+diagnostic?r.stageCode:null;
    const success=same&&revisionMatch&&r.code==='READ_PREFLIGHT_COMPLETE'&&r.transactionReadVerified===true&&phase==='COMPLETE'&&
      ((diagnostic==='DOCUMENT_PRESENT'&&r.documentFound===true)||(diagnostic==='DOCUMENT_ABSENT'&&r.documentFound===false));
    const failed=same&&revisionMatch&&r.transactionReadVerified===false&&['TRANSACTION_READ_NOT_VERIFIED','TRANSACTION_API_UNAVAILABLE'].includes(r.code)&&phase!=='COMPLETE'&&stage;
    const lines=['身份是否核验成功：'+(identity?'服务端报告成功':'未获服务端确认'),
      '当前 UID 与可信身份一致：'+(identity?(same?'是':'否（UID 或环境不一致）'):'尚未核实'),
      '云函数修订标记：'+(revisionMatch?manifest.revision:'缺失或不匹配（未展示原始值）'),
      '事务读取状态：'+(success?'本次读取成功':failed?'未通过':'尚未核实（版本、身份或诊断字段缺失/不一致）'),
      'phase：'+(phase||'未提供或未识别'),
      'diagnosticCode：'+(diagnostic||'未提供或未识别'),
      'stageCode：'+(stage||(success?'不适用（成功无阶段错误）':'未提供或不一致')),
      '结果代码：'+(known.has(r.code)?r.code:'未识别（未展示原文）'),
      '是否存在本人文档：'+(success?(r.documentFound?'是':'否（正常空结果）'):'未知（不能据失败判定不存在）'),
      '重新认证证明、并发写入、底层设备令牌撤销：未核实'];
    output.textContent=lines.join('\n');
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
