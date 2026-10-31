/* Offline party controllers. Shared navigation, lifecycle, storage and challenge bridge. */
(function(){
 'use strict';
 const C=window.HBPartyCore,KEY='hb_party_local_v1',types=['bomb','charades','taboo','score'];
 const titles={bomb:'数字炸弹',charades:'你演我猜',taboo:'别让我做',score:'聚会记分板'};
 let active=null,link=null,truthSession=null,timer=null,deadline=0,lastTap=0,readError='';
 let data={version:1,boards:[],results:[],custom:{charades:[],truth:[],dare:[]}};
 try{const raw=localStorage.getItem(KEY);if(raw)data=C.validateStore(JSON.parse(raw))}catch(e){readError='本地玩法数据读取失败，已保留原始内容。请先备份或检查存储空间。'}
 const e=s=>escapeHtml(s),button=(text,action,kind='secondary',disabled=false)=>`<button class="${kind}" onclick="HBParty.${action}" ${disabled?'disabled':''}>${text}</button>`;
 function header(type,subtitle){return `<header class="hp-heading"><div><span class="hb-tag">一起玩 · ${type==='score'?'本地记分':'无需联网'}</span><h2>${titles[type]}</h2></div><span class="hp-symbol hp-symbol-${type}">${icon(type)}</span></header><p class="hint">${subtitle}</p>`}
 function icon(type){const paths={bomb:'M12 7a7 7 0 1 0 5 2M12 7l3-3 3 3-3 3M18 3l1-2m2 6 2-1',charades:'M4 5h16v14H4zM8 9h.1M16 9h.1M8 13q4 5 8 0',taboo:'M4 8h16v12H4zM8 8V4h8v4M8 13h8M8 16h5',score:'M5 3h14v18H5zM9 7h6M9 12h6M9 17h6'};return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[type]}"/></svg>`}
 function lines(text,min=1,max=500){const a=C.unique(String(text).split(/\r?\n/));if(a.length<min||a.length>max||a.some(x=>x.length>80))throw Error(`请每行填写一项，共 ${min}～${max} 项，每项不超过 80 字`);return a}
 function commit(change){
  if(readError){toast(readError);return false}
  try{const next=JSON.parse(JSON.stringify(data));change(next);C.validateStore(next);localStorage.setItem(KEY,JSON.stringify(next));data=next;return true}catch(err){toast('未保存：'+err.message);return false}
 }
 function modal(title,body,accept,label='保存'){
  $('rtModalShade')?.remove();const shade=document.createElement('div');shade.id='rtModalShade';shade.className='rt-modal-shade';
  shade.innerHTML=`<div class="rt-modal hp-modal" role="dialog" aria-modal="true"><h3>${e(title)}</h3>${body}<div class="rt-modal-actions"><button class="secondary" id="rtCancel">取消</button><button class="primary" id="rtAccept">${e(label)}</button></div></div>`;
  document.body.appendChild(shade);$('rtCancel').onclick=()=>shade.remove();$('rtAccept').onclick=()=>{try{if(accept()!==false)shade.remove()}catch(err){toast(err.message)}};
 }
 function feedback(){vibrate(22);sfx('paper')}
 function tapped(){const now=performance.now();if(now-lastTap<280)return true;lastTap=now;return false}
 function stop(){clearInterval(timer);timer=null}
 function orientation(mode){
  document.body.classList.toggle('hp-task-display',!!active&&active.type==='taboo'&&active.visible);
  if(window.RandomToolboxNative?.setPartyOrientation){RandomToolboxNative.setPartyOrientation(mode||'auto');return}
  if(mode==='auto'){try{screen.orientation?.unlock()}catch(_){}return}
  if(screen.orientation?.lock)screen.orientation.lock(mode==='landscape'?'landscape':'portrait').catch(()=>toast('当前预览不支持锁定方向，请旋转设备；任务布局已切换'));
 }
 function cleanup(){stop();if(active?.type==='taboo'){active.visible=false;orientation('auto')}active=null;document.body.classList.remove('hp-task-display')}
 function open(type){if(!types.includes(type))return;cleanup();link=null;openGame(type)}
 function init(type){
  if(active?.type===type)return;
  cleanup();active={type,stage:'setup'};
  if(type==='bomb')Object.assign(active,{min:1,max:100,bomb:null});
  if(type==='charades')Object.assign(active,{category:'animal',seconds:60,mode:'action',left:60000,words:[],i:0,right:[],skipped:[],saved:false});
  if(type==='taboo')Object.assign(active,{n:4,category:'action',direction:'portrait',round:1,index:0,tasks:[],used:[],visible:false});
  if(type==='score')Object.assign(active,{page:'list',boardId:null});
 }
 function setStage(stage){active.stage=stage;party.stage=stage}
 function redraw(){if(!active)return;renderGame()}
 function render(type,box){
  if(!types.includes(type))return false;init(type);party.stage=active.stage;
  if(type==='score'){$('game').querySelector('.back').textContent=active.page==='ledger'?'‹ 返回记分板':active.page==='board'?'‹ 返回场次':'‹ 返回趣味玩法';window.HBScore.render(box);return true}
  box.innerHTML=`<div class="gamebox hp-game hp-${type}">${type==='bomb'?renderBomb():type==='charades'?renderCharades():renderTaboo()}</div>`;
  if(type==='taboo')document.body.classList.toggle('hp-task-display',active.visible);
  return true;
 }
 function bombStart(){
  if(active?.type!=='bomb'||tapped())return;
  try{if(active.stage==='setup'&&(!$('hpMin').value.trim()||!$('hpMax').value.trim()))throw Error('请填写最小值和最大值');const min=active.stage==='setup'?Number($('hpMin').value):active.min,max=active.stage==='setup'?Number($('hpMax').value):active.max;active.bomb=C.bomb(min,max,rand);active.min=min;active.max=max;setStage('play');redraw();feedback();$('hpGuess')?.focus()}catch(err){toast(err.message)}
 }
 function bombGuess(){
  if(active?.type!=='bomb'||active.stage!=='play'||tapped())return;
  try{if(!$('hpGuess').value.trim())throw Error('先输入一个数字');const hit=C.guess(active.bomb,Number($('hpGuess').value));if(hit){setStage('end');redraw();explosion();vibrate(300)}else{redraw();feedback();$('hpGuess').focus()}}catch(err){toast(err.message)}
 }
 function explosion(){const c=soundReady();if(!c)return;const t=c.currentTime,buffer=c.createBuffer(1,Math.floor(c.sampleRate*.55),c.sampleRate),a=buffer.getChannelData(0);for(let i=0;i<a.length;i++)a[i]=(Math.random()*2-1)*Math.exp(-i/(a.length*.16));const source=c.createBufferSource(),filter=c.createBiquadFilter(),gain=c.createGain();source.buffer=buffer;filter.type='lowpass';filter.frequency.setValueAtTime(1600,t);filter.frequency.exponentialRampToValueAtTime(80,t+.5);gain.gain.value=.28*settings.volume/100;source.connect(filter);filter.connect(gain);gain.connect(c.destination);source.start();source.onended=()=>{source.disconnect();filter.disconnect();gain.disconnect()}}
 function challengeButtons(){return `<div class="hp-two">${button('真心话',"challenge('truth')")}${button('大冒险',"challenge('dare')")}</div>`}
 function renderBomb(){
  const g=active,b=g.bomb;let html=header('bomb','轮流猜一个数。范围会越来越小，躲开藏在其中的数字炸弹。');
  if(g.stage==='setup')return html+`<div class="hp-hero hp-bomb-art">${icon('bomb')}</div><div class="hp-two"><label>最小值<input id="hpMin" type="number" inputmode="numeric" value="${g.min}" step="1"></label><label>最大值<input id="hpMax" type="number" inputmode="numeric" value="${g.max}" step="1"></label></div><p class="hint">边界也可能藏着炸弹，至少设置两个整数。一次只输入一个数。</p>${button('开始游戏','bombStart()','primary')}`;
  html+=`<div class="hp-range ${b.ended?'hp-explode':''}" role="status"><small>${b.ended?'砰！这次被选中了':'当前可猜范围'}</small><strong>${b.ended?e(b.secret):e(b.low)+' <span>—</span> '+e(b.high)}</strong><p>${b.ended?'第 '+b.history.length+' 次猜测踩中了炸弹':'轮到第 '+(b.history.length+1)+' 位，接住这一点悬念'}</p>${b.ended?'<i></i><i></i><i></i><i></i><i></i>':''}</div>`;
  if(!b.ended)html+=`<form class="hp-guess" onsubmit="event.preventDefault();HBParty.bombGuess()"><input id="hpGuess" aria-label="猜测数字" type="number" step="1" inputmode="numeric" min="${b.low}" max="${b.high}" placeholder="输入范围内的整数" required><button class="primary" type="submit">确认</button></form>${button('重新开始',"restartBomb()")}`;
  else html+=button('再来一局','bombStart()','primary')+challengeButtons()+button('返回玩法列表',"leave()")+button('修改数字范围',"bombSetup()");
  html+=`<details class="hp-records" ${b.ended?'open':''}><summary>猜测记录 · ${b.history.length} 次</summary>${b.history.length?`<ol>${b.history.map((h,i)=>`<li><span>第 ${i+1} 次 · ${h.value}</span><small>${h.hit?'踩中炸弹':h.value<b.secret?'偏小':'偏大'}</small></li>`).join('')}</ol>`:'<p class="hint">还没有人猜过，炸弹数字保持隐藏。</p>'}</details>`;return html;
 }
 function restartBomb(){if(active?.type!=='bomb')return;rtDialog('重新开始本局？','将清除猜测记录，并随机生成新的炸弹数字。',()=>bombStart())}
 function bombSetup(){if(active?.type!=='bomb'||active.stage!=='end')return;setStage('setup');active.bomb=null;redraw()}
 function categoryOptions(group,current){return Object.entries(window.HB_PARTY_LIBRARY[group]).map(([key,v])=>`<option value="${key}" ${current===key?'selected':''}>${v.label}</option>`).join('')}
 function charadesConfig(key,value){if(active?.type!=='charades'||active.stage!=='setup')return;if(key==='category'&&(HB_PARTY_LIBRARY.charades[value]||value==='custom'))active.category=value;if(key==='seconds'&&[30,60,90,120].includes(Number(value)))active.seconds=Number(value);if(key==='mode'&&['action','describe'].includes(value))active.mode=value}
 function editWords(){
  if(active?.type!=='charades'||active.stage!=='setup')return;
  modal('我的猜词题库',`<p class="hint">每行只写一个词语。按键盘换行后再写下一项，保存后选择“自定义”即可使用。</p><textarea id="hpCustomWords" rows="8" placeholder="大猩猩&#10;刷牙&#10;摄影师">${e((data.custom.charades||[]).join('\n'))}</textarea>`,()=>{const words=lines($('hpCustomWords').value,2);if(!commit(d=>d.custom.charades=words))return false;active.category='custom';redraw();toast('已保存')});
 }
 function charadesReady(){
  if(active?.type!=='charades'||active.stage!=='setup'||tapped())return;
  const words=active.category==='custom'?data.custom.charades:HB_PARTY_LIBRARY.charades[active.category]?.words.split('|');
  if(!words||words.length<2)return toast('请先添加至少两个自定义词语');
  active.words=shuffleGame([...words]);active.i=0;active.right=[];active.skipped=[];active.left=active.seconds*1000;active.saved=false;setStage('ready');redraw();
 }
 function charadesBegin(){
  if(active?.type!=='charades'||!['ready','paused'].includes(active.stage)||tapped())return;
  stop();deadline=performance.now()+active.left;setStage('play');redraw();feedback();timer=setInterval(charadesTick,100);
 }
 function charadesTick(){
  if(active?.type!=='charades'||active.stage!=='play'){stop();return}
  active.left=Math.max(0,deadline-performance.now());if(active.left<=0){charadesFinish();return}
  const label=$('hpClock');if(label)label.textContent=Math.ceil(active.left/1000)+' 秒';
 }
 function pause(){
  if(active?.type!=='charades'||active.stage!=='play')return;
  active.left=Math.max(0,deadline-performance.now());stop();if(active.left<=0){charadesFinish();return}setStage('paused');redraw();
 }
 function charadesAnswer(correct){
  if(active?.type!=='charades'||active.stage!=='play'||tapped())return;
  if(performance.now()>=deadline){charadesFinish();return}
  const word=active.words[active.i];(correct?active.right:active.skipped).push(word);active.i++;feedback();
  if(active.i>=active.words.length){charadesFinish();return}redraw();
 }
 function charadesFinish(){
  if(active?.type!=='charades'||!['play','paused','ready'].includes(active.stage))return;stop();active.left=Math.max(0,active.left);setStage('end');
  const result={id:uid(),at:Date.now(),category:active.category,mode:active.mode,seconds:active.seconds,right:[...active.right],skipped:[...active.skipped]};
  active.saved=commit(d=>{d.results.unshift(result);d.results=d.results.slice(0,100)});redraw();sfx('result');vibrate(150);
 }
 function charadesEnd(){if(active?.type!=='charades')return;pause();rtDialog('结束本轮？','将保存当前成绩，尚未作答的词语不计入跳过。',charadesFinish)}
 function charadesReset(){if(active?.type!=='charades'||active.stage!=='end')return;setStage('setup');redraw()}
 function results(){
  modal('本地猜词成绩',`<div class="hp-records">${data.results.length?data.results.map(r=>`<p><strong>${e(HB_PARTY_LIBRARY.charades[r.category]?.label||'自定义')} · 猜对 ${r.right.length} 题</strong><br><small>${new Date(r.at).toLocaleString()} · ${r.seconds} 秒 · 跳过 ${r.skipped.length} 题</small></p>`).join(''):'<p>完成一轮后，成绩会保存在这部手机。</p>'}</div>`,()=>true,'关闭');
 }
 function renderCharades(){
  const g=active;let html=header('charades','一人看词表演，其他人猜。请让猜词的人背对屏幕。');
  if(g.stage==='setup')return html+`<label>词语类别<select id="hpCategory" onchange="HBParty.charadesConfig('category',this.value)">${categoryOptions('charades',g.category)}<option value="custom" ${g.category==='custom'?'selected':''}>自定义（${data.custom.charades?.length||0} 个词）</option></select></label><div class="hp-two"><label>每轮时长<select onchange="HBParty.charadesConfig('seconds',this.value)">${[30,60,90,120].map(s=>`<option value="${s}" ${g.seconds===s?'selected':''}>${s} 秒</option>`).join('')}</select></label><label>表演方式<select onchange="HBParty.charadesConfig('mode',this.value)"><option value="action" ${g.mode==='action'?'selected':''}>纯动作</option><option value="describe" ${g.mode==='describe'?'selected':''}>语言描述</option></select></label></div><p class="hp-note">纯动作：不能说话或拼字。语言描述：不能说出答案中的字，也不要直接报出谐音。</p>${button('准备开始','charadesReady()','primary')}<div class="hp-two">${button('自定义词库','editWords()')}${button('本地成绩','results()')}</div>`;
  if(g.stage==='ready'||g.stage==='paused')return html+`<div class="hp-private"><span>${hbIcon(g.stage==='paused'?'pause':'user')}</span><h3>${g.stage==='paused'?'暂停，答案已收起':'把屏幕交给表演者'}</h3><p>猜词的人请移开视线。表演者确认后，才会展示词语并开始计时。</p><small>剩余 ${Math.ceil(g.left/1000)} 秒 · ${g.mode==='action'?'只做动作，不说话':'描述时避开答案中的字'}</small></div>${button(g.stage==='paused'?'继续游戏':'准备好了，显示词语','charadesBegin()','primary')}${button('结束本轮','charadesEnd()')}`;
  if(g.stage==='end')return html+`<div class="hp-result"><small>本轮成绩</small><strong>${g.right.length}<span> 题猜对</span></strong><p>跳过 ${g.skipped.length} 题 · ${g.i>=g.words.length?'本组词语已用完':'本轮结束'}</p></div><p class="hint">${g.saved?'成绩已保存在本机，最多保留最近 100 轮。':'成绩未能保存，请检查本地存储空间。'}</p><div class="hp-records"><h3>猜对的词</h3><p>${e(g.right.join('、')||'这一轮先热身')}</p><h3>跳过的词</h3><p>${e(g.skipped.join('、')||'没有跳过')}</p></div>${button('再来一轮','charadesReset()','primary')}`;
  return html+`<div class="hp-clock" role="timer" id="hpClock">${Math.ceil(g.left/1000)} 秒</div><div class="hp-word" aria-live="polite">${e(g.words[g.i])}</div><p class="hp-count">猜对 ${g.right.length} · 跳过 ${g.skipped.length}</p><div class="hp-two hp-answer-buttons">${button('跳过','charadesAnswer(false)')}${button('猜对了','charadesAnswer(true)','primary')}</div><div class="hp-two">${button('暂停','pause()')}${button('结束本轮','charadesEnd()')}</div>`;
 }
 function tabooConfig(key,value){if(active?.type!=='taboo'||active.stage!=='setup')return;if(key==='n')active.n=Number(value);if(key==='category'&&HB_PARTY_LIBRARY.taboo[value])active.category=value;if(key==='direction'&&['portrait','landscape'].includes(value))active.direction=value}
 function tabooTask(){const bank=HB_PARTY_LIBRARY.taboo[active.category].words.split('|').filter(w=>!active.used.includes(w));if(!bank.length)return null;const task=pick(bank);active.used.push(task);return task}
 function tabooStart(){
  if(active?.type!=='taboo'||active.stage!=='setup'||tapped())return;
  if(!Number.isInteger(active.n)||active.n<2||active.n>10)return toast('请选择 2～10 位玩家');
  active.used=[];active.tasks=[];for(let i=0;i<active.n;i++)active.tasks.push(tabooTask());active.index=0;active.round=1;active.visible=false;setStage('play');redraw();feedback();
 }
 function tabooShow(){
  if(active?.type!=='taboo'||active.stage!=='play'||active.visible)return;
  const g=active,index=g.index;
  rtDialog('请交给其他玩家操作',`当前为 ${index+1} 号玩家的任务。请让这位玩家先移开视线，并把屏幕朝向其他人，再点击展示。`,()=>{if(active!==g||g.index!==index||g.stage!=='play')return;g.visible=true;orientation(g.direction);redraw()});$('rtAccept').textContent='已准备好，展示任务';
 }
 function tabooHide(){if(active?.type!=='taboo')return;active.visible=false;orientation('auto');redraw()}
 function tabooDirection(){if(active?.type!=='taboo')return;active.direction=active.direction==='portrait'?'landscape':'portrait';if(active.visible)orientation(active.direction);redraw()}
 function tabooSuccess(){
  if(active?.type!=='taboo'||active.stage!=='play'||!active.visible||tapped())return;
  const g=active;g.visible=false;orientation('auto');redraw();
  rtDialog('确认挑战已触发？',`由其他玩家确认 ${g.index+1} 号玩家刚才自然完成了任务。`,()=>{if(active!==g)return;setStage('success');redraw();sfx('result');vibrate(100)});
 }
 function tabooNext(redrawTask=false){
  if(active?.type!=='taboo'||!['success','play'].includes(active.stage)||tapped())return;
  const g=active;
  if(redrawTask){const task=tabooTask();if(!task)return toast('这类任务已抽完，请结束本局后重新开始');g.tasks[g.index]=task}
  else{g.index++;if(g.index>=g.n){const available=HB_PARTY_LIBRARY.taboo[g.category].words.split('|').filter(w=>!g.used.includes(w));if(available.length<g.n){g.index=g.n-1;return toast('剩余任务不足一轮，请结束本局后重新开始')}g.index=0;g.round++;g.tasks=Array.from({length:g.n},()=>tabooTask())}}
  g.visible=false;orientation('auto');setStage('play');redraw();
 }
 function renderTaboo(){
  const g=active;let html=header('taboo','让别人自然做出自己的任务。本人不看答案，由其他玩家帮忙操作。');
  if(g.stage==='setup')return html+`<ol class="hp-rules"><li>每人分配一个任务，本人不能看。</li><li>轮到谁，就让谁移开视线；其他人接过手机，再点展示。</li><li>屏幕朝向其他人，目标玩家可以把手机放在额头或胸前。不要让目标玩家操作屏幕。</li><li>通过聊天自然引导，任务触发后由其他人确认。单台手机轮流展示，不同时分发私人屏幕。</li></ol><div class="hp-two"><label>参与人数<input id="hpTabooN" type="number" min="2" max="10" value="${g.n}" onchange="HBParty.tabooConfig('n',this.value)"></label><label>任务类别<select onchange="HBParty.tabooConfig('category',this.value)">${categoryOptions('taboo',g.category)}</select></label></div><label>展示方向<select onchange="HBParty.tabooConfig('direction',this.value)"><option value="portrait" ${g.direction==='portrait'?'selected':''}>竖屏 · 手持展示</option><option value="landscape" ${g.direction==='landscape'?'selected':''}>横屏 · 大字展示</option></select></label>${button('分配任务','tabooStart()','primary')}<p class="hint">默认隐藏，交接时自动收起。任何人都可以跳过不舒服的任务。</p>`;
  if(g.stage==='success')return html+`<div class="hp-result"><small>挑战触发</small><strong>${g.index+1} <span>号玩家</span></strong><p>大家的默契，再加一分。</p></div>${button(g.index===g.n-1?'进入下一轮':'下一位玩家','tabooNext()','primary')}${button('为这位玩家重新抽取','tabooNext(true)')}${challengeButtons()}`;
  const controls=`<div class="hp-two">${button(g.direction==='portrait'?'切换横屏':'切换竖屏','tabooDirection()')}${button(g.visible?'隐藏任务':'展示任务',g.visible?'tabooHide()':'tabooShow()')}</div>`;
  if(g.visible)return `<div class="hp-task-screen ${g.direction}" aria-live="polite"><div class="hp-task-top"><span>第 ${g.round} 轮 · ${g.index+1} 号玩家的任务</span>${button('隐藏任务','tabooHide()')}</div><strong>${e(g.tasks[g.index])}</strong><p>请让目标玩家背对屏幕</p><div class="hp-two">${button(g.direction==='portrait'?'切换横屏':'切换竖屏','tabooDirection()')}${button('挑战成功','tabooSuccess()','primary')}</div></div>`;
  return html+`<div class="hp-private"><span>${hbIcon('user')}</span><h3>${g.index+1} 号玩家，请先移开视线</h3><p>第 ${g.round} 轮 · 任务已隐藏</p><p>由其他玩家接过手机，确认屏幕朝向正确后再展示。目标玩家全程不看屏幕。</p></div>${controls}${button('跳过这位玩家','tabooSkip()')}<p class="hint">每位玩家都轮流体验一次后，自动分配下一轮的新任务。本局已用任务不会重复。</p>`;
 }
 function tabooSkip(){if(active?.type!=='taboo'||active.visible)return;rtDialog('跳过当前玩家？','收起任务，交给下一位玩家的朋友操作。',()=>tabooNext())}
 function challenge(mode){
  if(!['truth','dare'].includes(mode)||!active||!((active.type==='bomb'&&active.bomb?.ended)||(active.type==='taboo'&&active.stage==='success'))||tapped())return;
  stop();const source=active,sourceParty=party;link={source,sourceParty,label:titles[source.type]+(source.type==='taboo'?' · '+(source.index+1)+' 号玩家':' · 第 '+source.bomb.history.length+' 次猜测')};active=null;
  openGame('truth');if(truthSession)party=truthSession;party.stage='play';gamePrompt(mode);truthSession=party;
 }
 function truthExtras(box){if(party.type!=='truth')return;if(link)$('game').querySelector('.back').textContent='‹ 返回'+titles[link.source.type];const banner=document.createElement('div');banner.className='hp-truth-extras';banner.innerHTML=(link?`<p class="hp-source">来自 ${e(link.label)}</p>${button('完成挑战，返回'+titles[link.source.type],'returnChallenge()','primary')}`:'')+button('自定义挑战题库','editTruth()');box.appendChild(banner)}
 function truthBank(mode,base){return C.unique([...base,...(data.custom[mode]||[])])}
 function editTruth(){
  const session=party;
  modal('自定义挑战题库',`<p class="hint">原有题库保留。每行一条新增题目，保存后即可抽取；本局已抽过的题目不会重复。</p><label>真心话<textarea id="hpCustomTruth" rows="4">${e((data.custom.truth||[]).join('\n'))}</textarea></label><label>大冒险<textarea id="hpCustomDare" rows="4">${e((data.custom.dare||[]).join('\n'))}</textarea></label>`,()=>{if(party!==session)return false;const truth=lines($('hpCustomTruth').value,0),dare=lines($('hpCustomDare').value,0);if(!commit(d=>{d.custom.truth=truth;d.custom.dare=dare}))return false;renderGame();toast('已保存')});
 }
 function returnChallenge(){
  if(!link)return;truthSession=party;const previous=link;link=null;active=previous.source;party=previous.sourceParty;redraw();go('game');window.scrollTo(0,0);
 }
 function beforeBack(){
  if(link){rtDialog('返回原玩法？','当前挑战会收起，返回后可以继续原来的游戏。',returnChallenge);return true}
  if(active?.type==='score'&&active.page==='ledger'){active.page='board';redraw();return true}
  if(active?.type==='score'&&active.page==='board'){active.page='list';active.boardId=null;setStage('setup');redraw();return true}
  return false;
 }
 function guardNavigate(id){
  if(id==='game'||!$('game')?.classList.contains('active')||(!active&&!link))return false;
  if(link){rtDialog('退出本次挑战和原玩法？','退出后，原玩法的本局进度将结束。',()=>{link=null;truthSession=party;cleanup();party.stage='end';go(id)});return true}
  const current=active;
  if(current.type==='charades')pause();
  if(current.type==='taboo'&&current.visible)tabooHide();
  const needs=current.stage!=='setup'&&current.stage!=='end';
  if(needs){rtDialog('离开'+titles[current.type]+'？',current.type==='score'?'账目已自动保存在本机，可以从历史场次继续查看。':'离开后本局进度将结束。计时玩法已暂停，取消后可手动继续。',()=>{if(active!==current)return;cleanup();party.stage='end';go(id)});return true}
  cleanup();party.stage='end';return false;
 }
 function background(){if(active?.type==='charades')pause();if(active?.type==='taboo'&&active.visible)tabooHide()}
 function uid(){return Date.now().toString(36)+'-'+crypto.getRandomValues(new Uint32Array(2)).join('-')}
 document.addEventListener('visibilitychange',()=>{if(document.hidden)background()});window.addEventListener('pagehide',background);
 window.hbPartyPause=background;
 document.addEventListener('DOMContentLoaded',()=>{
  const menu=$('games');
  for(const type of types){const row=document.createElement('button');row.className='row hp-menu-row';row.onclick=()=>open(type);row.innerHTML=`<span class="hp-symbol hp-symbol-${type}">${icon(type)}</span><span class="info"><strong>${titles[type]}</strong><small>${{bomb:'范围越小，心跳越快',charades:'比一比默契，演出你的脑洞',taboo:'别让朋友猜到你的任务',score:'记录每一局，账目留在本机'}[type]}</small></span>${hbIcon('chevron')}`;menu.appendChild(row)}
  document.addEventListener('pointerdown',ev=>{if(ev.target.closest('.hp-game button,.hp-task-screen button'))vibrate(10)},{passive:true});
 });
 window.HBParty={open,render,truthExtras,truthBank,guardNavigate,beforeBack,background,modal,commit,lines,uid,redraw,setStage,button,header,e,
  get active(){return active},get data(){return data},get readError(){return readError},
  bombStart,bombGuess,restartBomb,bombSetup,charadesConfig,editWords,charadesReady,charadesBegin,charadesAnswer,charadesEnd,charadesReset,pause,results,
  tabooConfig,tabooStart,tabooShow,tabooHide,tabooDirection,tabooSuccess,tabooNext,tabooSkip,challenge,returnChallenge,editTruth,leave:()=>go('games')};
})();
