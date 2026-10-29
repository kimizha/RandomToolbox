from pathlib import Path
import os, json

p=Path('app/src/main/assets/index.html')
s=p.read_text(encoding='utf-8')
key=os.environ.get('CLOUDBASE_PUBLISHABLE_KEY','').strip()
if not key: raise SystemExit('Missing CLOUDBASE_PUBLISHABLE_KEY repository secret')
if not key.startswith('eyJ'): raise SystemExit('Unexpected Publishable Key format')
if 'RT_AUTH_FULLSCREEN_V2' in s: raise SystemExit('Account patch already present')

def replace(old,new):
 global s
 if old not in s: raise SystemExit('HTML anchor not found: '+old[:65])
 s=s.replace(old,new,1)

replace('function openGame(type){party=',"function openGame(type){if(!window.rtLoggedIn){rtShowLogin('登录后才能开始趣味玩法');return}party=")
replace('<section id="games" class="view">','<section id="games" class="view"><div id="rtGuestBanner" class="panel" style="padding:15px;margin-bottom:12px"><strong>🔒 登录后解锁趣味玩法</strong><p class="hint">游客可以继续使用随机工具和音乐播放器。</p><button class="primary" onclick="rtShowLogin()">登录 / 注册</button></div>')
replace('<section id="settings" class="view">','<section id="settings" class="view"><div class="panel" style="padding:16px;margin-bottom:14px"><h2>👤 我的账号</h2><p class="hint" id="rtUserStatus">游客模式</p><button id="rtLoginButton" class="primary" onclick="rtShowLogin()">登录 / 注册</button><button id="rtLogoutButton" class="secondary" style="display:none;width:100%" onclick="rtLogout()">退出登录</button></div>')

css=r'''<style id="rt-auth-style">
.rt-auth{position:fixed;inset:0;z-index:999999;background:radial-gradient(ellipse at 85% 0%,#e9ddff 0%,transparent 55%),#f8f8fc;color:#242039;overflow:auto;overscroll-behavior:contain;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.rt-auth *{box-sizing:border-box}.rt-wrap{max-width:430px;margin:auto;padding:calc(env(safe-area-inset-top) + 18px) 26px calc(env(safe-area-inset-bottom) + 40px);min-height:100dvh}.rt-back{border:0;background:#ffffffaa;border-radius:14px;width:44px;height:44px;color:inherit;font-size:24px;cursor:pointer}.rt-head{margin:36px 0 28px}.rt-icon{display:grid;place-items:center;width:70px;height:70px;border-radius:23px;background:linear-gradient(135deg,#b58cff,#7452e9);color:white;font-size:34px;box-shadow:0 12px 28px #8156dd45;margin-bottom:25px}.rt-head h1{font-size:32px;letter-spacing:-1px;margin:0 0 9px;font-weight:800}.rt-head p{font-size:14px;color:#87839a;margin:0;line-height:1.7}.rt-field{margin:16px 0}.rt-field label{display:block;font-size:13px;font-weight:650;margin:0 0 9px;color:#59546b}.rt-input{display:flex;align-items:center;background:#fff;border:1px solid #ece9f3;border-radius:17px;padding:0 15px;min-height:57px;box-shadow:0 3px 12px #32226706}.rt-input:focus-within{border-color:#a187ef;box-shadow:0 0 0 3px #a187ef20}.rt-input input{border:0;outline:0;background:transparent;color:inherit;font-size:15px;width:100%;min-width:0}.rt-eye{border:0;background:transparent;color:#8a839d;font-size:19px;padding:7px}.rt-btn{border:0;border-radius:17px;min-height:54px;width:100%;font-size:16px;font-weight:750;cursor:pointer}.rt-primary{background:linear-gradient(115deg,#a17af4,#7856e6);color:white;box-shadow:0 10px 22px #7e5ad63b}.rt-primary:disabled{opacity:.5}.rt-link{background:transparent;border:0;color:#8059e4;font-weight:700;font-size:14px;cursor:pointer;padding:10px}.rt-center{text-align:center}.rt-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.rt-message{min-height:22px;font-size:13px;color:#b15b70;line-height:1.6;margin:12px 0}.rt-card{display:flex;align-items:center;gap:15px;width:100%;padding:19px 17px;border:1px solid #eee9f8;border-radius:21px;background:#fff;margin:14px 0;text-align:left;color:inherit;box-shadow:0 8px 22px #47347d09}.rt-card-icon{display:grid;place-items:center;width:50px;height:50px;border-radius:16px;background:#f1eaff;font-size:25px}.rt-card b{font-size:16px}.rt-card small{display:block;color:#918ba1;margin-top:6px;font-size:12px}.rt-card-arrow{margin-left:auto;color:#aaa3b8;font-size:23px}.rt-otp{margin-top:12px}.rt-help{color:#928b9f;font-size:12px;line-height:1.7;margin-top:18px}.rt-auth[hidden]{display:none!important}
@media(prefers-color-scheme:dark){.rt-auth{background:radial-gradient(ellipse at 85% 0%,#382857 0%,transparent 55%),#15141d;color:#f7f4ff}.rt-back,.rt-input,.rt-card{background:#252331;border-color:#3b364c}.rt-head p,.rt-card small,.rt-field label{color:#aca6bc}.rt-input input{color:#fff}}
</style>'''
js=r'''
/* RT_AUTH_FULLSCREEN_V2 */
window.rtLoggedIn=false;
let rtAuth=null,rtVerify=null,rtPage='login',rtKind='email',rtBusy=false,rtCountdown=null,rtCurrentUser=null;
function rtAccountUI(){
 const guest=!window.rtLoggedIn;
 const b=document.getElementById('rtGuestBanner');if(b)b.style.display=guest?'block':'none';
 const status=document.getElementById('rtUserStatus');if(status)status.textContent=guest?'游客模式 · 趣味玩法需要登录':('已登录 · '+(rtCurrentUser?.username||rtCurrentUser?.email||rtCurrentUser?.phone||'趣味玩法已解锁'));
 const a=document.getElementById('rtLoginButton');if(a)a.style.display=guest?'block':'none';
 const z=document.getElementById('rtLogoutButton');if(z)z.style.display=guest?'none':'block';
}
function rtShowLogin(note){
 if(window.rtLoggedIn)return;
 let root=document.getElementById('rtAuthRoot');if(!root){root=document.createElement('div');root.id='rtAuthRoot';root.className='rt-auth';document.body.appendChild(root)}
 root.hidden=false;rtRender('login',note);
}
function rtCloseLogin(){const root=document.getElementById('rtAuthRoot');if(root)root.hidden=true;rtVerify=null;clearInterval(rtCountdown)}
function rtRender(page,note){
 rtPage=page;clearInterval(rtCountdown);const root=document.getElementById('rtAuthRoot');if(!root)return;
 const top='<div class="rt-wrap"><button class="rt-back" onclick="rtBack()" aria-label="返回">‹</button>';
 const head=(icon,title,sub)=>`<div class="rt-head"><div class="rt-icon">${icon}</div><h1>${title}</h1><p>${sub}</p></div>`;
 const input=(id,label,placeholder,type='text',extra='')=>`<div class="rt-field"><label for="${id}">${label}</label><div class="rt-input"><input id="${id}" type="${type}" placeholder="${placeholder}" ${extra}>${type==='password'?`<button class="rt-eye" type="button" onclick="rtTogglePassword('${id}',this)" aria-label="显示密码">◉</button>`:''}</div></div>`;
 const foot='<p id="rtMsg" class="rt-message" role="status"></p></div>';
 let html=top;
 if(page==='login'){
 html+=head('✦','欢迎回来','登录随机工具箱，解锁更多有趣玩法')+input('rtIdentifier','账号','用户名 / 邮箱 / 手机号','text','autocomplete="username"')+input('rtPassword','密码','请输入登录密码','password','autocomplete="current-password"')+'<div class="rt-row"><span></span><button class="rt-link" onclick="rtRender(\'forgot\')">忘记密码？</button></div><button class="rt-btn rt-primary" onclick="rtLogin()">登 录</button><p class="rt-center" style="margin-top:25px;color:#8e879c">还没有账号？<button class="rt-link" onclick="rtRender(\'choose\')">立即注册 →</button></p>';
 }else if(page==='choose'){
 html+=head('✧','创建新账号','选择适合你的方式，开启一点新惊喜')+[['phone','📱','手机号注册','通过短信验证码创建账号'],['email','✉️','邮箱注册','通过邮箱验证码创建账号'],['username','👤','账号密码注册','只需用户名和密码，无需绑定联系方式']].map(([k,ic,t,d])=>`<button class="rt-card" onclick="rtChoose('${k}')"><span class="rt-card-icon">${ic}</span><span><b>${t}</b><small>${d}</small></span><span class="rt-card-arrow">›</span></button>`).join('')+'<p class="rt-center" style="margin-top:28px">已有账号？<button class="rt-link" onclick="rtRender(\'login\')">返回登录</button></p>';
 }else if(page==='register'){
 const isPhone=rtKind==='phone',isUser=rtKind==='username';
 html+=head(isPhone?'📱':isUser?'👤':'✉️',isPhone?'手机号注册':isUser?'账号密码注册':'邮箱注册',isUser?'无需邮箱或手机号，注册后建议绑定找回方式':'完成身份验证后，即可使用趣味玩法');
 if(isUser)html+=input('rtName','用户名','5–24 位英文、数字或允许的符号','text','autocomplete="username"');
 if(!isUser)html+=input('rtContact',isPhone?'手机号':'邮箱地址',isPhone?'例如 +8613800138000':'请输入邮箱地址',isPhone?'tel':'email',isPhone?'autocomplete="tel"':'autocomplete="email"');
 html+=input('rtNewPassword','设置密码','请设置安全密码','password','autocomplete="new-password"')+input('rtConfirmPassword','确认密码','再次输入密码','password','autocomplete="new-password"')+'<button class="rt-btn rt-primary" onclick="rtRegister()">'+(isUser?'创建账号':'发送验证码')+'</button><p class="rt-help">'+(isUser?'请妥善保存密码。未绑定邮箱或手机号时，忘记密码可能无法找回；注册后可在账号安全中心绑定。':'注册时将向你的手机号或邮箱发送验证码。')+'</p>';
 }else if(page==='verify'){
 html+=head('✉','验证身份','验证码已发送，请检查短信或邮箱')+input('rtOtp','验证码','输入收到的验证码','text','inputmode="numeric" autocomplete="one-time-code"')+'<button class="rt-btn rt-primary" onclick="rtFinishRegister()">验证并完成注册</button><p class="rt-center"><button id="rtResend" class="rt-link" onclick="rtResend()">重新发送验证码</button></p>';
 }else if(page==='forgot'){
 html+=head('🔐','找回密码','请通过 CloudBase 账号恢复流程重置密码')+'<p class="rt-help">当前版本尚未接入安全的密码重置流程，请暂时返回登录。我们不会通过普通注册操作替你重置密码。</p><button class="rt-btn rt-primary" onclick="rtRender(\'login\')">返回登录</button>';
 }
 root.innerHTML=html+foot;if(note)rtMessage(note,false);
}
function rtBack(){if(rtPage==='login')rtCloseLogin();else if(rtPage==='choose')rtRender('login');else if(rtPage==='verify')rtRender('register');else rtRender('choose')}
function rtChoose(kind){rtKind=kind;rtRender('register')}
function rtTogglePassword(id,btn){const el=document.getElementById(id);el.type=el.type==='password'?'text':'password';btn.textContent=el.type==='password'?'◉':'◎'}
function rtMessage(msg,isError=true){const el=document.getElementById('rtMsg');if(el){el.textContent=msg;el.style.color=isError?'#b15b70':'#7b5ed0'}}
function rtError(e){return e?.message||e?.error_description||String(e||'请求失败')}
function rtCheck(result){if(result?.error)throw result.error;return result?.data}
async function rtFinishAuth(result){
 const data=rtCheck(result);const session=await rtAuth.getSession();rtCheck(session);
 window.rtLoggedIn=!!(session?.data?.session||data?.session);rtCurrentUser=data?.user||session?.data?.user||null;
 if(!window.rtLoggedIn)throw Error('尚未获得有效登录会话');rtAccountUI();rtCloseLogin();if(typeof toast==='function')toast('登录成功 ✨');
}
async function rtLogin(){
 if(rtBusy)return;if(!rtAuth)return rtMessage('登录服务尚未连接，请检查网络');
 const id=document.getElementById('rtIdentifier').value.trim(),password=document.getElementById('rtPassword').value;
 if(!id||!password)return rtMessage('请填写账号和密码');
 let field=id.includes('@')?{email:id}:/^\+?\d{7,15}$/.test(id)?{phone:id}:{username:id};
 rtBusy=true;try{await rtFinishAuth(await rtAuth.signInWithPassword({...field,password}))}catch(e){rtMessage(rtError(e))}finally{rtBusy=false}
}
async function rtRegister(){
 if(rtBusy)return;if(!rtAuth)return rtMessage('注册服务尚未连接，请检查网络');
 const contact=document.getElementById('rtContact')?.value.trim()||'',password=document.getElementById('rtNewPassword').value,confirm=document.getElementById('rtConfirmPassword').value;
 const name=rtKind==='username'?document.getElementById('rtName').value.trim():null;
 if(rtKind==='phone'&&!/^\+\d{8,15}$/.test(contact))return rtMessage('手机号请使用国际格式，例如 +8613800138000');
 if(rtKind==='email'&&!/^\S+@\S+\.\S+$/.test(contact))return rtMessage('请输入有效邮箱');
 if(name&&!/^[A-Za-z0-9][A-Za-z0-9_.:+@-]{4,23}$/.test(name))return rtMessage('用户名须为 5–24 位，且以字母或数字开头');
 if(password.length<8)return rtMessage('密码至少 8 位');if(password!==confirm)return rtMessage('两次密码不一致');
 rtBusy=true;try{
 const params={...(rtKind==='phone'?{phone:contact}:rtKind==='email'?{email:contact}:{}),password,...(name?{username:name}:{})};
 const result=await rtAuth.signUp(params);const data=rtCheck(result);
 if(rtKind==='username'){
   if(typeof data?.verifyOtp==='function')throw Error('当前环境仍要求验证码，请检查用户名密码注册配置');
   try{await rtFinishAuth(result)}catch(e){await rtFinishAuth(await rtAuth.signInWithPassword({username:name,password}))}
   return;
 }
 if(typeof data?.verifyOtp!=='function')throw Error('未收到验证码验证接口，请检查登录方式配置');
 rtVerify=data.verifyOtp;rtRender('verify');rtTimer();
 }catch(e){rtMessage(rtError(e))}finally{rtBusy=false}
}
async function rtFinishRegister(){
 if(rtBusy)return;const token=document.getElementById('rtOtp').value.trim();if(!token)return rtMessage('请输入验证码');
 if(typeof rtVerify!=='function')return rtMessage('验证码已失效，请返回重新发送');
 rtBusy=true;try{await rtFinishAuth(await rtVerify({token}))}catch(e){rtMessage(rtError(e))}finally{rtBusy=false}
}
function rtTimer(){let sec=60;const b=document.getElementById('rtResend');if(!b)return;b.disabled=true;b.textContent=`${sec} 秒后可重新发送`;rtCountdown=setInterval(()=>{sec--;const x=document.getElementById('rtResend');if(!x){clearInterval(rtCountdown);return}x.disabled=sec>0;x.textContent=sec>0?`${sec} 秒后可重新发送`:'返回重新发送';if(sec<=0)clearInterval(rtCountdown)},1000)}
function rtResend(){rtVerify=null;rtRender('register');rtMessage('请再次提交注册信息以重新获取验证码',false)}
async function rtLogout(){if(!rtAuth)return;if(rtBusy)return;try{rtCheck(await rtAuth.signOut());window.rtLoggedIn=false;rtCurrentUser=null;rtAccountUI();if(typeof toast==='function')toast('已退出登录')}catch(e){if(typeof toast==='function')toast(rtError(e))}}
async function rtStartAuth(){
 try{
 const sdk=window.RTCloudbaseSDK; if(!sdk)throw Error('本地 CloudBase SDK 加载失败');
 const app=sdk.init({env:'randomtoolbox-d5gg1p6rg1d2287eb',region:'ap-shanghai',accessKey:__RT_PUBLISHABLE_KEY__});
 rtAuth=typeof app.auth==='function'?app.auth():app.auth;
 const r=await rtAuth.getSession();rtCheck(r);window.rtLoggedIn=!!r?.data?.session;rtCurrentUser=r?.data?.user||null;rtAccountUI();
 }catch(e){console.error('CloudBase auth initialization failed',e);rtAccountUI()}
}
rtAccountUI();rtStartAuth();
'''
js=js.replace('__RT_PUBLISHABLE_KEY__',json.dumps(key))
replace('</head>',css+'</head>')
replace('<script>', '<script src="cloudbase-sdk.js"></script><script>')
replace('</script></body></html>',js+'\n</script></body></html>')
p.write_text(s,encoding='utf-8')
print('Injected fullscreen account UI')
