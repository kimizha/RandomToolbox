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
 function icon(type){const i=types.indexOf(type),x=i%2*627,y=Math.floor(i/2)*627;return `<svg viewBox="${x} ${y} 627 627" aria-hidden="true"><image href="ui/party-icons.png" width="1254" height="1254"/></svg>`}
 function selectCard(label,value,action){return `<button class="hp-select-card" onclick="HBParty.${action}"><small>${label}</small><strong>${e(value)}</strong>${hbIcon('chevron')}</button>`}
 function chooseCharades(key){
  if(active?.type!=='charades'||active.stage!=='setup')return;
  const options=key==='category'?{mixed:'混合版',...Object.fromEntries(Object.entries(HB_PARTY_LIBRARY.charades).map(([k,v])=>[k,v.label]))}:key==='mode'?{mixed:'语言 + 动作',action:'纯动作',describe:'语言描述'}:{30:'30 秒',60:'60 秒',90:'90 秒',120:'120 秒'};
  modal(key==='category'?'这次猜哪一类？':key==='mode'?'选择表演方式':'每轮玩多久？',`<div class="hp-option-grid">${Object.entries(options).map(([v,label])=>button(e(label),`applyChoice('${key}','${v}')`,'hp-option '+(String(active[key])===v?'selected':''))).join('')}</div><p class="hint">${key==='category'?'混合版会打乱全部六类词语，每轮不重复。':key==='mode'?'语言 + 动作：可以边说边演，但不要说出答案中的字。':'选择后立即应用。'}</p>`,()=>true,'完成');
 }
 function applyChoice(key,value){charadesConfig(key,value);$('rtModalShade')?.remove();redraw()}
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
  document.body.classList.toggle('hp-task-display',!!active&&active.type==='taboo'&&(active.visible||active.counting));
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
  if(type==='charades')Object.assign(active,{category:'mixed',seconds:60,mode:'mixed',left:60000,words:[],i:0,right:[],skipped:[]});
  if(type==='taboo')Object.assign(active,{n:1,guests:0,direction:'portrait',round:1,index:0,tasks:[],used:[],visible:false,counting:false,hasShown:false});
  if(type==='score')Object.assign(active,{page:'list',boardId:null});
 }
 function setStage(stage){active.stage=stage;party.stage=stage}
 function redraw(){if(!active)return;renderGame()}
 function render(type,box){
  if(!types.includes(type))return false;init(type);party.stage=active.stage;
  if(type==='score'){$('game').querySelector('.back').textContent=active.page==='ledger'?'‹ 返回记分板':active.page==='board'?'‹ 返回场次':'‹ 返回趣味玩法';window.HBScore.render(box);return true}
  box.innerHTML=`<div class="gamebox hp-game hp-${type}">${type==='bomb'?renderBomb():type==='charades'?renderCharades():renderTaboo()}</div>`;
  if(type==='taboo')document.body.classList.toggle('hp-task-display',(active.visible||active.counting));
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
  else html+=button('再来一局','bombStart()','primary')+button('进入真心话大冒险',"challenge('choose')");
  return html;
 }
 function restartBomb(){if(active?.type!=='bomb')return;rtDialog('重新开始本局？','将随机生成新的炸弹数字，重新开始这一局。',()=>bombStart())}
 function bombSetup(){if(active?.type!=='bomb'||active.stage!=='end')return;setStage('setup');active.bomb=null;redraw()}
 function categoryOptions(group,current){return Object.entries(window.HB_PARTY_LIBRARY[group]).map(([key,v])=>`<option value="${key}" ${current===key?'selected':''}>${v.label}</option>`).join('')}
 function charadesConfig(key,value){if(active?.type!=='charades'||active.stage!=='setup')return;if(key==='category'&&(HB_PARTY_LIBRARY.charades[value]||value==='mixed'))active.category=value;if(key==='seconds'&&[30,60,90,120].includes(Number(value)))active.seconds=Number(value);if(key==='mode'&&['action','describe','mixed'].includes(value))active.mode=value}
 function charadesReady(){
  if(active?.type!=='charades'||active.stage!=='setup'||tapped())return;
  const words=active.category==='mixed'?C.unique(Object.values(HB_PARTY_LIBRARY.charades).flatMap(v=>v.words.split('|'))):HB_PARTY_LIBRARY.charades[active.category]?.words.split('|');
  if(!words?.length)return;
  active.words=shuffleGame([...words]);active.i=0;active.right=[];active.skipped=[];active.left=active.seconds*1000;setStage('ready');redraw();
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
  redraw();sfx('result');vibrate(150);
 }
 function charadesEnd(){if(active?.type!=='charades')return;pause();rtDialog('结束本轮？','本轮将立即结束，尚未作答的词语不计入跳过。',charadesFinish)}
 function charadesReset(){if(active?.type!=='charades'||active.stage!=='end')return;setStage('setup');redraw()}
 function renderCharades(){
  const g=active;let html=header('charades','一人看词表演，其他人猜。请让猜词的人背对屏幕。');
  if(g.stage==='setup')return html+`<div class="hp-selection-stack">${selectCard('词语类别',g.category==='mixed'?'混合版 · 全部六类随机抽取':HB_PARTY_LIBRARY.charades[g.category].label,"chooseCharades('category')")}${selectCard('表演方式',({mixed:'语言 + 动作',action:'纯动作',describe:'语言描述'})[g.mode],"chooseCharades('mode')")}${selectCard('每轮时长',g.seconds+' 秒',"chooseCharades('seconds')")}</div><p class="hp-note">一人看词，其他人猜。${g.mode==='mixed'?'可以边说边演，但不能说出答案中的字。':g.mode==='action'?'只用动作表达，不说话、不拼字。':'用语言描述，避开答案中的字和直接谐音。'}猜对就换题，不会可以跳过。</p>${button('准备开始','charadesReady()','primary')}`;
  if(g.stage==='ready'||g.stage==='paused')return html+`<div class="hp-private"><span>${hbIcon(g.stage==='paused'?'pause':'user')}</span><h3>${g.stage==='paused'?'暂停，答案已收起':'把屏幕交给表演者'}</h3><p>猜词的人请移开视线。表演者确认后，才会展示词语并开始计时。</p><small>剩余 ${Math.ceil(g.left/1000)} 秒 · ${g.mode==='action'?'只做动作，不说话':g.mode==='mixed'?'可以边说边演，避开答案中的字':'描述时避开答案中的字'}</small></div>${button(g.stage==='paused'?'继续游戏':'准备好了，显示词语','charadesBegin()','primary')}${button('结束本轮','charadesEnd()')}`;
  if(g.stage==='end')return html+`<div class="hp-result"><small>本轮成绩</small><strong>${g.right.length}<span> 题猜对</span></strong><p>跳过 ${g.skipped.length} 题 · ${g.i>=g.words.length?'本组词语已用完':'本轮结束'}</p></div><div class="hp-records"><h3>猜对的词</h3><p>${e(g.right.join('、')||'这一轮先热身')}</p><h3>跳过的词</h3><p>${e(g.skipped.join('、')||'没有跳过')}</p></div>${button('再来一轮','charadesReset()','primary')}`;
  return html+`<div class="hp-clock" role="timer" id="hpClock">${Math.ceil(g.left/1000)} 秒</div><div class="hp-word" aria-live="polite">${e(g.words[g.i])}</div><p class="hp-count">猜对 ${g.right.length} · 跳过 ${g.skipped.length}</p><div class="hp-two hp-answer-buttons">${button('跳过','charadesAnswer(false)')}${button('猜对了','charadesAnswer(true)','primary')}</div><div class="hp-two">${button('暂停','pause()')}${button('结束本轮','charadesEnd()')}</div>`;
 }
 function tabooConfig(key,value){if(active?.type!=='taboo'||active.stage!=='setup')return;if(key==='direction'&&['portrait','landscape'].includes(value)){active.direction=value;redraw()}}
 function chooseGuests(){
  if(active?.type!=='taboo'||active.stage!=='setup')return;
  modal('加入未安装 App 的朋友',`<p class="hint">选择的人数不包含你自己。比如选 2 位朋友，会生成 3 个任务：先分给朋友，最后一个留给机主。</p><div class="hp-option-grid">${Array.from({length:10},(_,n)=>button(n===0?'只有我自己':n+' 位朋友',`setGuests(${n})`,'hp-option '+(active.guests===n?'selected':''))).join('')}</div>`,()=>true,'完成');
 }
 function setGuests(n){if(active?.type!=='taboo'||active.stage!=='setup'||!Number.isInteger(n)||n<0||n>9)return;active.guests=n;active.n=n+1;$('rtModalShade')?.remove();redraw()}
 function tabooBank(){return C.unique(Object.values(HB_PARTY_LIBRARY.taboo).flatMap(v=>v.words.split('|')))}
 function tabooTask(){const bank=tabooBank().filter(w=>!active.used.includes(w));if(!bank.length)return null;const task=pick(bank);active.used.push(task);return task}
 function taskOwner(g=active){return g.index===g.n-1?'机主本人':'朋友 '+(g.index+1)}
 function tabooStart(){
  if(active?.type!=='taboo'||active.stage!=='setup'||tapped())return;
  active.used=[];active.tasks=Array.from({length:active.n},()=>tabooTask());active.index=0;active.round=1;active.visible=false;active.counting=false;active.hasShown=false;setStage('play');redraw();feedback();
 }
 function tabooShow(){
  if(active?.type!=='taboo'||active.stage!=='play'||active.visible||active.counting||tapped())return;
  const g=active,seconds=g.guests>0&&!g.hasShown?5:3;stop();g.counting=true;g.countLeft=seconds;deadline=performance.now()+seconds*1000;orientation(g.direction);redraw();
  timer=setInterval(()=>{if(active!==g||!g.counting){stop();return}g.countLeft=Math.max(0,Math.ceil((deadline-performance.now())/1000));if(!g.countLeft){stop();g.counting=false;g.visible=true;g.hasShown=true;redraw();feedback()}else if($('hpCountdown'))$('hpCountdown').textContent=g.countLeft},80);
 }
 function tabooHide(){if(active?.type!=='taboo')return;stop();active.counting=false;active.visible=false;orientation('auto');redraw()}
 function tabooDirection(){if(active?.type!=='taboo')return;active.direction=active.direction==='portrait'?'landscape':'portrait';if(active.visible||active.counting)orientation(active.direction);redraw()}
 function tabooSuccess(){
  if(active?.type!=='taboo'||active.stage!=='play'||!active.visible||tapped())return;
  const g=active,owner=taskOwner(g);tabooHide();
  rtDialog('确认挑战已触发？',`确认${owner}已经自然完成任务？请由其他玩家确认。`,()=>{if(active!==g)return;setStage('success');redraw();sfx('result');vibrate(100)});
 }
 function tabooNext(redrawTask=false){
  if(active?.type!=='taboo'||!['success','play'].includes(active.stage)||active.counting||tapped())return;
  const g=active;
  if(redrawTask){const task=tabooTask();if(!task)return toast('任务已抽完，请退出后重新开始');g.tasks[g.index]=task}
  else if(g.index<g.n-1)g.index++;
  else{if(tabooBank().filter(w=>!g.used.includes(w)).length<g.n)return toast('剩余任务不足一轮，请退出后重新开始');g.index=0;g.round++;g.tasks=Array.from({length:g.n},()=>tabooTask())}
  stop();g.visible=false;g.counting=false;orientation('auto');setStage('play');redraw();
 }
 function renderTaboo(){
  const g=active,own=g.index===g.n-1;let html=header('taboo','你的任务，只有别人知道。聊着聊着，小心就中招了。');
  if(g.stage==='setup')return html+`<div class="hp-howto"><h3>怎么玩？</h3><ol class="hp-rules"><li><strong>每人一个秘密任务。</strong>任务可能是说一句话，或做一个动作；你不能看自己的内容。</li><li><strong>看别人的，藏好自己的。</strong>点击“显示任务”后，把屏幕背对自己，让其他玩家记住你的任务。</li><li><strong>自然聊天，互相引导。</strong>例如任务是“说出我不知道”，朋友可以问个难题，诱导你说出这句话。</li><li><strong>被引导完成任务，就中招。</strong>由其他人点击“挑战成功”，之后可换任务或接一个真心话、大冒险。</li><li><strong>朋友没有 App 也能玩。</strong>下方加入人数不含机主，先轮流分给朋友，每次都让当事人回避；最后一个任务属于你。每个人只记别人的任务。</li></ol></div><div class="hp-selection-stack">${selectCard('一起玩的朋友',g.guests?g.guests+' 位未安装 App 的朋友':'加入未安装 App 的朋友','chooseGuests()')}<div class="hp-direction"><small>展示方向</small><div class="hp-two">${button('竖屏',"tabooConfig('direction','portrait')",'hp-option '+(g.direction==='portrait'?'selected':''))}${button('横屏',"tabooConfig('direction','landscape')",'hp-option '+(g.direction==='landscape'?'selected':''))}</div></div></div>${button('开始游戏','tabooStart()','primary')}`;
  if(g.stage==='success')return html+`<div class="hp-result"><small>挑战触发</small><strong>${e(taskOwner())}</strong><p>大家的默契，再加一分。</p></div>${button(g.index===g.n-1?'进入下一轮':'分配下一个任务','tabooNext()','primary')}${button('为这位玩家重新抽取','tabooNext(true)')}${challengeButtons()}`;
  if(g.counting)return `<div class="hp-task-screen ${g.direction} hp-countdown-screen"><small>${own?'这是你的任务':'即将展示'+e(taskOwner())+'的任务'}</small><strong id="hpCountdown" role="timer">${g.countLeft}</strong><p>${own?'倒计时结束后将展示你的任务。请立即将手机背对自己，让其他玩家观看。':'请勿让被分配的玩家看屏幕。请机主和其他玩家记住任务，机主自己的任务在最后一个。'}</p>${button('取消展示','tabooHide()')}</div>`;
  if(g.visible)return `<div class="hp-task-screen ${g.direction}" aria-live="polite"><div class="hp-task-top"><span>第 ${g.round} 轮 · ${e(taskOwner())}的任务</span>${button('隐藏任务','tabooHide()')}</div><strong>让 TA ${e(g.tasks[g.index])}</strong><p>${own?'屏幕请始终背对机主本人':'只给机主和其他朋友看，请勿给'+e(taskOwner())+'观看'}</p><div class="hp-two">${button(g.index===g.n-1?'收起，准备下一轮':'收起，分配下一个','tabooNext()')}${button('挑战成功','tabooSuccess()','primary')}</div></div>`;
  return html+`<div class="hp-private"><span>${hbIcon('user')}</span><h3>${own?'这是您的提示词':e(taskOwner())+'的提示词'}</h3><p>${own?'点击显示后有 3 秒准备时间，请将手机背对自己，方便其他玩家观看。':'请勿给被分配玩家观看。由本机玩家及其他玩家查看、记住任务；本机玩家的提示词在最后一个。'}</p><small>第 ${g.round} 轮 · 第 ${g.index+1} / ${g.n} 个任务 · ${g.guests>0&&!g.hasShown?'首次展示倒计时 5 秒':'展示倒计时 3 秒'}</small></div>${button('显示任务','tabooShow()','primary')}${button(g.direction==='portrait'?'切换横屏':'切换竖屏','tabooDirection()')}`;
 }
 function challenge(mode){
  if(!['truth','dare','choose'].includes(mode)||!active||!((active.type==='bomb'&&active.bomb?.ended)||(active.type==='taboo'&&active.stage==='success'))||tapped())return;
  stop();const source=active,sourceParty=party;link={source,sourceParty,label:titles[source.type]+(source.type==='taboo'?' · '+taskOwner(source):' · 第 '+source.bomb.history.length+' 次猜测')};active=null;
  openGame('truth');if(truthSession)party=truthSession;party.stage='play';if(mode==='choose'){party.prompt='';renderGame()}else gamePrompt(mode);truthSession=party;
 }
 function truthExtras(box){if(party.type==='truth'&&link)$('game').querySelector('.back').textContent='‹ 返回'+titles[link.source.type]}
 function truthIntro(){return link?.source.type==='bomb'?button('返回数字炸弹','returnChallenge()','hp-return-bomb'):''}
 function truthBank(mode,base){return C.unique([...base,...(data.custom[mode]||[])])}
 function returnChallenge(){
  if(!link)return;truthSession=party;const previous=link;link=null;active=previous.source;party=previous.sourceParty;if(active.type==='bomb'){active.bomb=null;setStage('setup')}redraw();go('game');window.scrollTo(0,0);
 }
 function beforeBack(){
  if(link){rtDialog('返回原玩法？',link.source.type==='bomb'?'返回后可重新设置数字范围。':'当前挑战会收起，返回后可以继续原来的游戏。',returnChallenge);return true}
  if(active?.type==='score'&&active.page==='ledger'){active.page='board';redraw();return true}
  if(active?.type==='score'&&active.page==='board'){active.page='list';active.boardId=null;setStage('setup');redraw();return true}
  return false;
 }
 function guardNavigate(id){
  if(id==='game'||!$('game')?.classList.contains('active')||(!active&&!link))return false;
  if(link){rtDialog('退出本次挑战和原玩法？','退出后，原玩法的本局进度将结束。',()=>{link=null;truthSession=party;cleanup();party.stage='end';go(id)});return true}
  const current=active;
  if(current.type==='charades')pause();
  if(current.type==='taboo'&&(current.visible||current.counting))tabooHide();
  const needs=current.stage!=='setup'&&current.stage!=='end';
  if(needs){rtDialog('离开'+titles[current.type]+'？',current.type==='score'?'账目已自动保存在本机，可以从历史场次继续查看。':'离开后本局进度将结束。计时玩法已暂停，取消后可手动继续。',()=>{if(active!==current)return;cleanup();party.stage='end';go(id)});return true}
  cleanup();party.stage='end';return false;
 }
 function background(){if(active?.type==='charades')pause();if(active?.type==='taboo'&&(active.visible||active.counting))tabooHide()}
 function uid(){return Date.now().toString(36)+'-'+crypto.getRandomValues(new Uint32Array(2)).join('-')}
 document.addEventListener('visibilitychange',()=>{if(document.hidden)background()});window.addEventListener('pagehide',background);
 window.hbPartyPause=background;
 document.addEventListener('DOMContentLoaded',()=>{
  const menu=$('games');
  for(const type of types){const row=document.createElement('button');row.className='row hp-menu-row';row.onclick=()=>open(type);row.innerHTML=`<span class="hp-symbol hp-symbol-${type}">${icon(type)}</span><span class="info"><strong>${titles[type]}</strong><small>${{bomb:'范围越小，心跳越快',charades:'比一比默契，演出你的脑洞',taboo:'别让朋友猜到你的任务',score:'记录每一局，账目留在本机'}[type]}</small></span>${hbIcon('chevron')}`;menu.appendChild(row)}
  document.addEventListener('pointerdown',ev=>{if(ev.target.closest('.hp-game button,.hp-task-screen button'))vibrate(10)},{passive:true});
 });
 window.HBParty={open,render,truthExtras,truthIntro,truthBank,guardNavigate,beforeBack,background,modal,commit,lines,uid,redraw,setStage,button,header,e,
  get active(){return active},get data(){return data},get readError(){return readError},
  bombStart,bombGuess,restartBomb,bombSetup,charadesConfig,chooseCharades,applyChoice,charadesReady,charadesBegin,charadesAnswer,charadesEnd,charadesReset,pause,
  tabooConfig,chooseGuests,setGuests,tabooStart,tabooShow,tabooHide,tabooDirection,tabooSuccess,tabooNext,challenge,returnChallenge,leave:()=>go('games')};
})();
