
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
 html+=head('✧','创建新账号','选择适合你的方式，开启一点新惊喜')+[['phone','📱','手机号注册','通过短信验证码创建账号'],['email','✉️','邮箱注册','通过邮箱验证码创建账号'],['username','👤','账号密码注册','设置用户名，使用邮箱验证身份']].map(([k,ic,t,d])=>`<button class="rt-card" onclick="rtChoose('${k}')"><span class="rt-card-icon">${ic}</span><span><b>${t}</b><small>${d}</small></span><span class="rt-card-arrow">›</span></button>`).join('')+'<p class="rt-center" style="margin-top:28px">已有账号？<button class="rt-link" onclick="rtRender(\'login\')">返回登录</button></p>';
 }else if(page==='register'){
 const isPhone=rtKind==='phone',isUser=rtKind==='username';
 html+=head(isPhone?'📱':isUser?'👤':'✉️',isPhone?'手机号注册':isUser?'账号密码注册':'邮箱注册',isUser?'为保证账号安全，需要邮箱验证码完成注册':'完成身份验证后，即可使用趣味玩法');
 if(isUser)html+=input('rtName','用户名','5–24 位英文、数字或允许的符号','text','autocomplete="username"');
 html+=input('rtContact',isPhone?'手机号':'邮箱地址',isPhone?'例如 +8613800138000':'请输入邮箱地址',isPhone?'tel':'email',isPhone?'autocomplete="tel"':'autocomplete="email"');
 html+=input('rtNewPassword','设置密码','请设置安全密码','password','autocomplete="new-password"')+input('rtConfirmPassword','确认密码','再次输入密码','password','autocomplete="new-password"')+'<button class="rt-btn rt-primary" onclick="rtRegister()">发送验证码</button><p class="rt-help">注册时将向你的手机号或邮箱发送验证码。用户名注册也需要验证邮箱。</p>';
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
 const contact=document.getElementById('rtContact').value.trim(),password=document.getElementById('rtNewPassword').value,confirm=document.getElementById('rtConfirmPassword').value;
 const name=rtKind==='username'?document.getElementById('rtName').value.trim():null;
 if(rtKind==='phone'&&!/^\+\d{8,15}$/.test(contact))return rtMessage('手机号请使用国际格式，例如 +8613800138000');
 if(rtKind!=='phone'&&!/^\S+@\S+\.\S+$/.test(contact))return rtMessage('请输入有效邮箱');
 if(name&&!/^[A-Za-z0-9][A-Za-z0-9_.:+@-]{4,23}$/.test(name))return rtMessage('用户名须为 5–24 位，且以字母或数字开头');
 if(password.length<8)return rtMessage('密码至少 8 位');if(password!==confirm)return rtMessage('两次密码不一致');
 rtBusy=true;try{
 const params={...(rtKind==='phone'?{phone:contact}:{email:contact}),password,...(name?{username:name}:{})};
 const result=await rtAuth.signUp(params);const data=rtCheck(result);
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
 const mod=await import('https://esm.sh/@cloudbase/js-sdk@3?bundle');const sdk=mod.default||mod;
 const app=sdk.init({env:'randomtoolbox-d5gg1p6rg1d2287eb',region:'ap-shanghai',accessKey:__RT_PUBLISHABLE_KEY__});
 rtAuth=typeof app.auth==='function'?app.auth():app.auth;
 const r=await rtAuth.getSession();rtCheck(r);window.rtLoggedIn=!!r?.data?.session;rtCurrentUser=r?.data?.user||null;rtAccountUI();
 }catch(e){console.error('CloudBase auth initialization failed',e);rtAccountUI()}
}
rtAccountUI();rtStartAuth();
'''
js=js.replace('__RT_PUBLISHABLE_KEY__',json.dumps(key))
replace('</head>',css+'</head>')
replace('</script></body></html>',js+'\n</script></body></html>')
p.write_text(s,encoding='utf-8')
print('Injected fullscreen account UI')

