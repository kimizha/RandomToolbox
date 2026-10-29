
from pathlib import Path
import os

p=Path('app/src/main/assets/index.html')
s=p.read_text(encoding='utf-8')
if 'RT_CLOUDBASE_AUTH_V1' in s:
    print('Auth patch already present')
    raise SystemExit(0)
key=os.environ.get('CLOUDBASE_PUBLISHABLE_KEY','').strip()
if not key:
    raise SystemExit('Missing CLOUDBASE_PUBLISHABLE_KEY repository secret')
if not key.startswith('eyJ'):
    raise SystemExit('Unexpected Publishable Key format')
assert 'function openGame(type){party=' in s, 'Game entry not found'
s=s.replace('function openGame(type){party=', "function openGame(type){if(!window.rtLoggedIn){rtShowLogin('登录后才能开始趣味玩法');return}party=",1)
assert '<section id="games" class="view">' in s
s=s.replace('<section id="games" class="view">', '''<section id="games" class="view"><div id="rtGuestBanner" class="panel" style="padding:15px;margin-bottom:12px"><strong>🔒 登录后解锁趣味玩法</strong><p class="hint">游客可以继续使用随机工具和音乐播放器。</p><button class="primary" onclick="rtShowLogin()">登录 / 注册</button></div>''',1)
assert '<section id="settings" class="view">' in s
s=s.replace('<section id="settings" class="view">','''<section id="settings" class="view"><div class="panel" style="padding:16px;margin-bottom:14px"><h2>👤 账号</h2><p class="hint" id="rtUserStatus">游客模式</p><button id="rtLoginButton" class="primary" onclick="rtShowLogin()">登录 / 注册</button><button id="rtLogoutButton" class="secondary" style="display:none;width:100%" onclick="rtLogout()">退出登录</button></div>''',1)
js=r'''
/* RT_CLOUDBASE_AUTH_V1 */
window.rtLoggedIn=false;
let rtAuth=null,rtVerify=null,rtMode='login',rtBusy=false;
function rtAccountUI(){
  const banner=document.getElementById('rtGuestBanner');if(banner)banner.style.display=window.rtLoggedIn?'none':'block';
  const status=document.getElementById('rtUserStatus');if(status)status.textContent=window.rtLoggedIn?'已登录 · 趣味玩法已解锁':'游客模式 · 趣味玩法需要登录';
  const login=document.getElementById('rtLoginButton');if(login)login.style.display=window.rtLoggedIn?'none':'block';
  const logout=document.getElementById('rtLogoutButton');if(logout)logout.style.display=window.rtLoggedIn?'block':'none';
}
function rtShowLogin(note){
  if(document.getElementById('rtLoginShade'))return;
  const shade=document.createElement('div');shade.id='rtLoginShade';shade.className='rt-modal-shade';
  shade.innerHTML=`<div class="rt-modal" style="max-height:85vh;overflow:auto"><h2>👤 登录 / 注册</h2><p class="hint" id="rtLoginNote"></p><div class="field"><label>邮箱</label><input id="rtEmail" type="email" autocomplete="email" placeholder="请输入邮箱"></div><div class="field" style="margin-top:12px"><label>密码</label><input id="rtPassword" type="password" autocomplete="current-password" placeholder="请输入密码"></div><div class="field" id="rtOtpField" style="display:none;margin-top:12px"><label>邮箱验证码</label><input id="rtOtp" autocomplete="one-time-code" inputmode="numeric" placeholder="请输入验证码"></div><p class="hint" id="rtLoginMessage"></p><button class="primary" id="rtSubmit" onclick="rtSubmitLogin()">密码登录</button><div class="fields" style="margin-top:10px"><button class="secondary" onclick="rtSwitchMode('login')">密码登录</button><button class="secondary" onclick="rtSwitchMode('signup')">邮箱注册</button></div><button class="secondary" style="width:100%;margin-top:10px" onclick="rtCloseLogin()">取消</button></div>`;
  document.body.appendChild(shade);document.getElementById('rtLoginNote').textContent=note||'登录后即可解锁趣味玩法';rtSwitchMode('login');
}
function rtCloseLogin(){document.getElementById('rtLoginShade')?.remove();rtVerify=null}
function rtSwitchMode(mode){rtMode=mode;rtVerify=null;document.getElementById('rtOtpField').style.display='none';document.getElementById('rtLoginMessage').textContent=mode==='signup'?'注册将发送邮箱验证码':'请输入已注册账号';document.getElementById('rtSubmit').textContent=mode==='signup'?'发送验证码':'密码登录'}
function rtErr(e){return e?.message||e?.error_description||String(e||'请求失败')}
async function rtSubmitLogin(){
  if(rtBusy)return;const message=document.getElementById('rtLoginMessage');
  if(!rtAuth){message.textContent='登录服务未连接，请检查网络后重试';return}
  const email=document.getElementById('rtEmail').value.trim(),password=document.getElementById('rtPassword').value,otp=document.getElementById('rtOtp').value.trim();
  if(!email.includes('@')){message.textContent='请输入有效邮箱';return}
  if(rtMode!=='verify'&&!password){message.textContent='请输入密码';return}
  rtBusy=true;document.getElementById('rtSubmit').disabled=true;
  try{
    let result;
    if(rtMode==='login')result=await rtAuth.signInWithPassword({email,password});
    else if(rtMode==='signup'){
      result=await rtAuth.signUp({email,password});if(result?.error)throw result.error;
      if(typeof result?.data?.verifyOtp!=='function')throw Error('未能开始验证码验证');
      rtVerify=result.data.verifyOtp;rtMode='verify';document.getElementById('rtOtpField').style.display='block';document.getElementById('rtSubmit').textContent='验证并注册';message.textContent='验证码已发送，请查看邮箱';return;
    }else{if(!otp)throw Error('请输入验证码');result=await rtVerify({token:otp})}
    if(result?.error)throw result.error;
    const session=await rtAuth.getSession();if(session?.error)throw session.error;
    window.rtLoggedIn=!!session?.data?.session;
    if(!window.rtLoggedIn)throw Error('登录未返回有效会话');
    rtAccountUI();rtCloseLogin();toast('登录成功，已解锁趣味玩法');
  }catch(e){message.textContent=rtErr(e)}
  finally{rtBusy=false;const btn=document.getElementById('rtSubmit');if(btn)btn.disabled=false}
}
async function rtLogout(){if(!rtAuth)return toast('登录服务未连接');try{const r=await rtAuth.signOut();if(r?.error)throw r.error;window.rtLoggedIn=false;rtAccountUI();toast('已退出登录')}catch(e){toast(rtErr(e))}}
async function rtStartAuth(){
  try{
    const mod=await import('https://esm.sh/@cloudbase/js-sdk@3?bundle');
    const sdk=mod.default||mod;
    const app=sdk.init({env:'randomtoolbox-d5gg1p6rg1d2287eb',region:'ap-shanghai',accessKey:__RT_PUBLISHABLE_KEY__});
    rtAuth=app.auth;
    if(typeof rtAuth.onAuthStateChange==='function')rtAuth.onAuthStateChange((_event,session)=>{window.rtLoggedIn=!!session;rtAccountUI()});
    const result=await rtAuth.getSession();if(result?.error)throw result.error;
    window.rtLoggedIn=!!result?.data?.session;rtAccountUI();
  }catch(e){console.error('CloudBase auth init failed',e);window.rtLoggedIn=false;rtAccountUI()}
}
rtAccountUI();rtStartAuth();
'''
import json
js=js.replace('__RT_PUBLISHABLE_KEY__',json.dumps(key))
assert '</script></body></html>' in s
s=s.replace('</script></body></html>',js+'\n</script></body></html>',1)
p.write_text(s,encoding='utf-8')
print('Auth patch injected into',p)
