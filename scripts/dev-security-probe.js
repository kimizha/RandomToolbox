/* HAPPYBOX_SECURITY_PROBE_TEST_ONLY */
(() => {
  'use strict';
  try { if (RandomToolboxNative.isSecurityProbeTestBuild() !== true) return; } catch (_) { return; }
  const settingsView = document.getElementById('settings');
  if (!settingsView) return;
  const panel = document.createElement('section');panel.className = 'panel';panel.id = 'rtDevSecurityProbe';
  panel.innerHTML = '<h2>开发测试 · 只读安全核验</h2><p class="hint">线上源码尚未由客户端验证。先核对部署代码，再手动调用；不会发布公告或注册设备。</p><label style="display:flex;gap:10px;align-items:start"><input type="checkbox" style="width:18px;height:18px;flex:0 0 18px" id="rtProbeSourceChecked"><span>我已核对线上 index.js、probe.cjs 和依赖锁文件与 813c2f5 的部署包一致</span></label><button class="secondary" id="rtProbeRun" style="width:100%;margin-top:14px">使用当前真实会话核验</button><p id="rtProbeResult" role="status" style="white-space:pre-wrap;overflow-wrap:anywhere"></p>';
  settingsView.appendChild(panel);
  const run = panel.querySelector('#rtProbeRun'), output = panel.querySelector('#rtProbeResult');
  let busy = false;
  const uidOf = u => String(u?.uid || u?.id || u?._id || '');
  const current = () => window.rtLoggedIn === true ? uidOf(rtUser) : '';
  const known = new Set(['TRUSTED_IDENTITY_UNAVAILABLE','ENVIRONMENT_NOT_VERIFIED','REAL_USER_REQUIRED','PROBE_NOT_AUTHORIZED','TRANSACTION_API_UNAVAILABLE','TRANSACTION_READ_NOT_VERIFIED','READ_PREFLIGHT_COMPLETE']);
  async function bounded(promise) {
    let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('timeout')),10000);})]);}finally{clearTimeout(timer);}
  }
  run.onclick = async () => {
    if (busy) return;
    output.textContent = '';
    if (!panel.querySelector('#rtProbeSourceChecked').checked) {output.textContent='请先按校验清单核对线上源码。这个确认框不授予任何账号权限。';return;}
    const uid = current();
    if (!uid || typeof rtAuth === 'undefined' || !rtAuth || !window.rtCloudApp) {output.textContent='请先使用现有登录界面登录测试账号。';return;}
    busy=true;run.disabled=true;
    try {
      const sessionResult=await bounded(rtAuth.getSession());
      const session=sessionResult?.data?.session;
      if (sessionResult?.error || !session || uidOf(session.user || sessionResult.data.user)!==uid || current()!==uid) {
        output.textContent='有效会话未确认或账号已改变，请重新确认登录状态。';return;
      }
      const response=await bounded(window.rtCloudApp.callFunction({name:'happyboxSecurityProbe',data:{}}));
      if (current()!==uid) {output.textContent='账号已切换或退出，已丢弃旧账号的核验结果。';return;}
      const r=response?.result;
      if (response?.error || !r || typeof r!=='object' || Array.isArray(r) || !known.has(r.code)) {output.textContent='响应格式无法确认，未展示原始响应。';return;}
      if (r.ok!==true || r.identityVerified!==true) {output.textContent='云函数未确认身份：'+r.code+'。请检查测试 UID 名单、运行时与部署代码。';return;}
      if (r.environment!=='randomtoolbox-d5gg1p6rg1d2287eb' || r.uid!==uid) {output.textContent='服务端 UID 或环境与当前会话不一致，核验未通过。';return;}
      output.textContent='身份已核验：是\n本人 UID：'+uid+'\n环境：'+r.environment+'\n事务读取：'+(r.transactionReadVerified===true?'本次读取成功':'尚未核实')+'\n结果代码：'+r.code+'\n重新认证证明：本探针不核实\n事务并发写入：未核实\n底层设备令牌撤销：未核实\n此结果不能证明正式设备限制已完成。';
    } catch (_) {
      output.textContent=current()!==uid?'账号已改变，核验已结束。':'调用失败或超时，请检查网络、函数部署和调用权限。原始错误未输出。';
    } finally {busy=false;run.disabled=false;}
  };
})();
