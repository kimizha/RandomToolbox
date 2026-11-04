/* HAPPYBOX_SECURITY_PROBE_TEST_ONLY: manual, read-only SDK diagnostic. */
(() => {
 'use strict';
 try{if(window.RandomToolboxNative?.isSecurityProbeTestBuild()!==true)return}catch(_){return}
 const target=document.getElementById('settings');if(!target||document.getElementById('rtDevSecurityProbe'))return;
 const manifest=window.hbProbeExpected,files=['index.js','probe.cjs','transaction-read.cjs','package.json','package-lock.json','read-control.cjs'];
 const valid=manifest?.localSourceCheck==='MATCH'&&manifest.revision==='readonly-comparison-v3'&&/^[a-f0-9]{64}$/.test(manifest.packageSha256)&&files.every(n=>/^[a-f0-9]{64}$/.test(manifest.files?.[n]));
 const codes=new Set(['TRUSTED_IDENTITY_UNAVAILABLE','ENVIRONMENT_NOT_VERIFIED','REAL_USER_REQUIRED','PROBE_NOT_AUTHORIZED','TRANSACTION_API_UNAVAILABLE','TRANSACTION_READ_NOT_VERIFIED','READ_PREFLIGHT_COMPLETE']);
 const diagnostics=new Set(['DATABASE_INIT_FAILED','TRANSACTION_API_UNAVAILABLE','TRANSACTION_API_MISMATCH','TRANSACTION_UNSUPPORTED','PERMISSION_DENIED','DOCUMENT_PRESENT','DOCUMENT_ABSENT','DOCUMENT_NOT_FOUND_ERROR','COLLECTION_NOT_FOUND','READ_RESULT_INVALID','TRANSPORT_ERROR','UNCLASSIFIED_ERROR','CALLBACK_NOT_EXECUTED','READ_API_UNAVAILABLE','READ_API_MISMATCH','READ_UNSUPPORTED','ROUTING_TARGET_NOT_FOUND','NOT_COMPLETED','PROBE_BUDGET_EXCEEDED']);
 const phases=new Set(['START','READ','COMMIT','COMPLETE','UNKNOWN']);
 const localCodes=new Set(['SDK_NOT_READY','SYNC_NOT_PAUSED','SESSION_REQUIRED','SESSION_CHECK_FAILED','ACCOUNT_CHANGED','PROBE_FUNCTION_NOT_FOUND','PROBE_CALL_FAILED','PROBE_RESPONSE_INVALID','PROBE_TIMEOUT']);
 const panel=document.createElement('section');panel.id='rtDevSecurityProbe';panel.className='panel hb-probe';
 panel.innerHTML=`<h2>开发测试</h2><p class="hb-probe-intro">检查当前账号的数据库连接。仅查看状态，不上传本机配置。</p><button id="rtProbeRun" class="primary hb-probe-run"><i class="hb-probe-spinner" id="rtProbeSpinner" aria-hidden="true" hidden></i><span>数据库连接测试（只读）</span></button><div id="rtProbeResult" class="hb-probe-results" role="status" aria-live="polite"></div><button id="rtProbeCopy" class="secondary hb-probe-copy" disabled>复制诊断摘要</button><details class="hb-probe-details"><summary>版本与只读范围</summary><p id="rtProbeDeployment">线上源码摘要尚未核实；修订标记匹配不等于源码摘要已核实。</p><pre id="rtProbeManifest"></pre></details><p class="hb-probe-note">保持云端同步暂停。空集合返回 DOCUMENT_ABSENT 是正常结果。</p>`;
 target.appendChild(panel);
 const e=id=>panel.querySelector('#'+id),run=e('rtProbeRun'),copy=e('rtProbeCopy'),out=e('rtProbeResult'),spinner=e('rtProbeSpinner');
 e('rtProbeManifest').textContent=valid?'预期修订：'+manifest.revision+'\n本地包 SHA-256：'+manifest.packageSha256+'\n本地六个源文件与部署包一致；不代表线上包已核实。':'本地构建证据无效，核验不可用。';
 let inFlight=null,loading=false,halted=!valid,summary='',epoch=0;
 const empty=()=>({session:'尚未检查',identity:'尚未核实',environment:'尚未核实',revision:'尚未核实',ordinary:{status:'尚未核实',diagnostic:'—',stage:'—',found:'未知'},transaction:{status:'尚未核实',start:'尚未核实',read:'尚未核实',commit:'尚未核实',phase:'—',diagnostic:'—',stage:'—',code:'—',found:'未知'},conclusion:'尚未核验',message:'点击按钮开始本次只读检查。',backend:'—'});
 let model=empty();
 function controls(){run.disabled=halted||!!inFlight;spinner.hidden=!loading;run.setAttribute('aria-busy',String(loading));copy.disabled=!summary||loading}
 function section(title,rows){const box=document.createElement('div');box.className='hb-probe-part';const h=document.createElement('h3');h.textContent=title;box.appendChild(h);const dl=document.createElement('dl');for(const [label,value] of rows){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;dl.append(dt,dd)}box.appendChild(dl);out.appendChild(box)}
 function render(){
  out.replaceChildren();
  section('身份与版本',[['当前会话',model.session],['服务端身份',model.identity],['环境核对',model.environment],['修订标记',model.revision]]);
  const o=model.ordinary,t=model.transaction;
  section('普通文档读取',[['读取结果',o.status],['diagnosticCode',o.diagnostic],['stageCode',o.stage],['本人文档',o.found]]);
  section('事务读取',[['启动',t.start],['读取',t.read],['提交',t.commit],['phase',t.phase],['diagnosticCode',t.diagnostic],['stageCode',t.stage],['最终结果代码',t.code],['本人文档',t.found]]);
  const conclusion=document.createElement('div');conclusion.className='hb-probe-conclusion';const strong=document.createElement('strong'),p=document.createElement('span');strong.textContent=model.conclusion;p.textContent=model.message;conclusion.append(strong,p);out.appendChild(conclusion);
  summary=['开心盒 · 数据库连接测试（只读）','当前会话：'+model.session,'服务端身份：'+model.identity,'环境核对：'+model.environment,'修订标记：'+model.revision,'普通读取：'+o.status,'ordinary.diagnosticCode：'+o.diagnostic,'ordinary.stageCode：'+o.stage,'普通读取本人文档：'+o.found,'事务启动：'+t.start,'事务读取：'+t.read,'事务提交：'+t.commit,'phase：'+t.phase,'diagnosticCode：'+t.diagnostic,'stageCode：'+t.stage,'最终结果代码：'+t.code,'事务本人文档：'+t.found,'综合结论：'+model.conclusion,model.message,'服务端 comparisonCode：'+model.backend,'云端同步：保持暂停','线上源码摘要：尚未远程核实'].join('\n');controls();
 }
 function interpret(r,uid){
  const matched=r.probeRevision===manifest.revision;
  model.revision=matched?manifest.revision:'缺失或不匹配';
  model.identity=r.ok===true&&r.identityVerified===true?'服务端报告通过':'未通过';
  model.environment=r.environment==='randomtoolbox-d5gg1p6rg1d2287eb'?'匹配':'未核实或不匹配';
  if(!matched){model.conclusion='PROBE_REVISION_MISMATCH';model.message='线上修订不是预期 V3，已停止核验；不会自动部署或修改函数。';halted=true;return}
  if(r.ok!==true||r.identityVerified!==true||Object.hasOwn(r,'uid')&&r.uid!==uid){model.identity='未通过';model.conclusion='PROBE_NOT_AUTHORIZED';model.message='服务端身份或白名单未通过；未确认数据库访问。';halted=true;return}
  if(model.environment!=='匹配'){model.conclusion='BOTH_UNVERIFIED';model.message='环境不匹配，已停止核验。';halted=true;return}
  const o=r.ordinaryRead||{},t=r.transaction||{},od=diagnostics.has(o.diagnosticCode)?o.diagnosticCode:null,td=diagnostics.has(t.diagnosticCode)?t.diagnosticCode:null,phase=phases.has(t.phase)?t.phase:null;
  const found=(d,v)=>d==='DOCUMENT_PRESENT'&&v===true||d==='DOCUMENT_ABSENT'&&v===false;
  const ordinary=o.readVerified===true&&found(od,o.documentFound);
  const transaction=t.transactionReadVerified===true&&t.code==='READ_PREFLIGHT_COMPLETE'&&r.code===t.code&&r.transactionReadVerified===true&&phase==='COMPLETE'&&found(td,t.documentFound);
  const negative=d=>d&&!['DOCUMENT_PRESENT','DOCUMENT_ABSENT','NOT_COMPLETED'].includes(d);
  const ofailed=o.readVerified===false&&negative(od)&&o.stageCode==='ORDINARY_'+od;
  const tfailed=t.transactionReadVerified===false&&['START','READ','COMMIT','UNKNOWN'].includes(phase)&&negative(td)&&t.stageCode===phase+'_'+td&&['TRANSACTION_READ_NOT_VERIFIED','TRANSACTION_API_UNAVAILABLE'].includes(t.code)&&r.code===t.code&&r.transactionReadVerified===false;
  model.ordinary={status:ordinary?'本次成功':ofailed?'未通过':'尚未核实',diagnostic:od||'未提供或未识别',stage:ofailed?o.stageCode:ordinary?'不适用（成功）':'未提供或不一致',found:ordinary?(o.documentFound?'存在':'不存在（正常空结果）'):'未知'};
  model.transaction={status:transaction?'本次成功':tfailed?'未通过':'尚未核实',start:'尚未核实',read:'尚未核实',commit:'尚未核实',phase:phase||'未提供或未识别',diagnostic:td||'未提供或未识别',stage:tfailed?t.stageCode:transaction?'不适用（成功）':'未提供或不一致',code:codes.has(t.code)?t.code:codes.has(r.code)?r.code:'未提供或未识别',found:transaction?(t.documentFound?'存在':'不存在（正常空结果）'):'未知'};
  const tx=model.transaction;
  if(transaction)tx.start=tx.read=tx.commit='已完成';
  else if(tfailed&&phase==='START')Object.assign(tx,{start:'未通过',read:'未执行',commit:'未执行'});
  else if(tfailed&&phase==='READ')Object.assign(tx,{start:'已完成',read:'未通过',commit:'未执行'});
  else if(tfailed&&phase==='COMMIT')Object.assign(tx,{start:'已完成',read:'已完成',commit:'未通过'});
  const comparisons=new Set(['BOTH_READS_VERIFIED','ORDINARY_VERIFIED_TRANSACTION_FAILED','ORDINARY_FAILED_TRANSACTION_VERIFIED','BOTH_UNVERIFIED','PROBE_BUDGET_EXCEEDED','DATABASE_INIT_FAILED']);
  model.backend=comparisons.has(r.comparisonCode)?r.comparisonCode:'未提供或未识别';
  const expected=ordinary&&transaction?'BOTH_READS_VERIFIED':ordinary&&tfailed?'ORDINARY_VERIFIED_TRANSACTION_FAILED':ofailed&&transaction?'ORDINARY_FAILED_TRANSACTION_VERIFIED':ofailed&&tfailed?'BOTH_UNVERIFIED':null;
  if(expected&&r.comparisonCode===expected){model.conclusion=ordinary&&transaction?'BOTH_READS_VERIFIED':ordinary?'TRANSACTION_READ_FAILED':transaction?'ORDINARY_READ_FAILED':'BOTH_UNVERIFIED';model.message=ordinary&&transaction?'两种只读路径均通过。DOCUMENT_ABSENT 是正常空结果；未执行并发写入或设备限制测试。':ordinary?'普通读取通过，事务读取未通过。':transaction?'事务读取通过，普通读取未通过。':'两种读取均未通过，保留当前权限和同步暂停状态。'}
  else{model.conclusion=ordinary&&!transaction?'TRANSACTION_READ_FAILED':transaction&&!ordinary?'ORDINARY_READ_FAILED':'BOTH_UNVERIFIED';model.message='响应缺少有效证据或字段不一致，未确认综合成功。'}
 }
 function fail(code){
  const messages={SDK_NOT_READY:'SDK 尚未完成初始化，请稍后重试。',SYNC_NOT_PAUSED:'同步暂停状态未确认，已阻止调用。',SESSION_REQUIRED:'未确认有效登录会话，本次没有调用云函数。',SESSION_CHECK_FAILED:'会话检查失败，未展示原始错误或凭据。',ACCOUNT_CHANGED:'账号已切换或退出，已丢弃旧账号核验结果。',PROBE_FUNCTION_NOT_FOUND:'未找到现有云函数，已停止；不会自动创建或部署。',PROBE_CALL_FAILED:'云函数调用失败，请检查网络和已有函数状态。',PROBE_RESPONSE_INVALID:'云函数响应格式无法核实，未展示原始响应。',PROBE_TIMEOUT:'检查超时；上一请求结束前不会重复发送。'};
  if(code==='SESSION_REQUIRED')model.session='无有效会话';
  if(code==='SESSION_CHECK_FAILED')model.session='检查失败';
  if(code==='ACCOUNT_CHANGED'){model=empty();model.session='账号已改变'}
  model.conclusion=code==='SESSION_REQUIRED'?'PROBE_NOT_AUTHORIZED':code;
  model.message=messages[code];if(['PROBE_FUNCTION_NOT_FOUND','SYNC_NOT_PAUSED'].includes(code))halted=true;
 }
 run.onclick=async()=>{
  if(inFlight||halted)return;
  model=empty();model.message='正在检查当前真实会话…';loading=true;const own=++epoch;let finished=false,timer;
  const context=window.hbReadOnlyProbeContext;
  if(!context?.ready()){loading=false;fail('SDK_NOT_READY');render();return}
  const work=context.execute(()=>{if(!finished&&own===epoch){model.session='本次检查有效';render()}});inFlight=work;render();
  const release=()=>{if(inFlight===work){inFlight=null;controls()}};work.then(release,release);
  try{
   const answer=await Promise.race([work,new Promise((_,reject)=>{timer=setTimeout(()=>reject({code:'PROBE_TIMEOUT'}),12000)})]);
   if(own===epoch)interpret(answer.result,answer.expectedUid);
  }catch(e){if(own===epoch)fail(localCodes.has(e?.code)?e.code:'PROBE_CALL_FAILED')}
  finally{finished=true;clearTimeout(timer);loading=false;render()}
 };
 copy.onclick=async()=>{if(!summary||loading)return;const safe=summary;try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(safe);if(typeof toast==='function')toast('诊断摘要已复制');return}}catch(_){}const field=document.createElement('textarea');field.value=safe;field.readOnly=true;field.style.cssText='position:fixed;left:-9999px';document.body.appendChild(field);field.select();let ok=false;try{ok=document.execCommand('copy')}catch(_){}field.remove();if(typeof toast==='function')toast(ok?'诊断摘要已复制':'复制未成功，请重试')};
 if(!valid){model.conclusion='LOCAL_BUILD_EVIDENCE_INVALID';model.message='本地构建证据无效，已阻止调用。';render()}else controls();
})();
