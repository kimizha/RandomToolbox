/* Local, host-led lateral-thinking mysteries; answers are never sent to a service. */
const SOUP_LEVELS={all:'全部难度',easy:'轻松入门',medium:'进阶推理',hard:'烧脑挑战'};
function soupCases(){return window.RT_GAME_LIBRARY.soups}
function soupCurrent(){return soupCases().find(item=>item.id===party.soupId)}
function soupAvailable(){return soupCases().filter(item=>(party.soupDifficulty==='all'||item.difficulty===party.soupDifficulty)&&!party.soupUsed.includes(item.id))}
function setSoupDifficulty(value){if(party.type!=='soup'||party.stage!=='setup'||!Object.prototype.hasOwnProperty.call(SOUP_LEVELS,value))return;party.soupDifficulty=value;renderGame()}
function dealSoupCase(){
 const available=soupAvailable();if(!available.length){toast('这组题已全部玩过，重新开局后可再次抽取');return}
 const item=pick(available);party.soupId=item.id;party.soupUsed.push(item.id);party.soupHints=0;party.soupAnswerVisible=false;party.stage='play';renderGame();window.scrollTo(0,0);
}
function startSoupGame(){if(party.type==='soup'&&party.stage==='setup')dealSoupCase()}
function showSoupHint(){if(party.type!=='soup'||party.stage!=='play')return;const item=soupCurrent();if(!item||party.soupHints>=item.hints.length||party.soupAnswerVisible)return;party.soupHints++;renderGame()}
function showSoupHost(){
 if(party.type!=='soup'||party.stage!=='play')return;const item=soupCurrent(),session=party;if(!item)return;
 rtDialog('请先把手机交给主持人','下一步会显示汤底。请让其他玩家移开视线，查看完后点击“收起并交还手机”。',()=>{
  if(party!==session||party.soupId!==item.id)return;
  const shade=document.createElement('div');shade.id='rtModalShade';shade.className='rt-modal-shade';
  shade.innerHTML=`<div class="rt-modal hb-soup-host" role="dialog" aria-modal="true"><span class="hb-soup-tag">主持人专用</span><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.solution)}</p><h4>关键事实</h4><ul>${item.facts.map(f=>`<li>${escapeHtml(f)}</li>`).join('')}</ul><p class="hint">根据汤底回答“是／不是／不重要／无法确定”，不用临时补造情节。</p><button class="primary" id="soupHostClose">收起并交还手机</button></div>`;
  document.body.appendChild(shade);$('soupHostClose').onclick=()=>shade.remove();
 });$('rtAccept').textContent='我是主持人，查看汤底';
}
function revealSoupAnswer(){
 if(party.type!=='soup'||party.stage!=='play'||party.soupAnswerVisible)return;const session=party,item=soupCurrent();
 rtDialog('揭晓汤底？','确认后会向所有人展示本题答案。还想继续推理的话，可以先取消。',()=>{if(party!==session||party.soupId!==item?.id)return;party.soupAnswerVisible=true;renderGame()});$('rtAccept').textContent='揭晓汤底';
}
function nextSoupCase(){
 if(party.type!=='soup'||party.stage!=='play')return;if(!soupAvailable().length){toast('这组题已全部玩过，重新开局后可再次抽取');return}
 if(party.soupAnswerVisible){dealSoupCase();return}
 const session=party,id=party.soupId;rtDialog('换一道海龟汤？','当前题目尚未揭晓，换题后本轮不会再抽到它。',()=>{if(party===session&&party.soupId===id)dealSoupCase()});$('rtAccept').textContent='换下一题';
}
function resetSoupGame(){
 if(party.type!=='soup')return;const session=party;
 rtDialog('重新开始海龟汤？','将清除本轮已玩记录并返回难度选择，之前的题目可能再次出现。',()=>{
  if(party!==session)return;party.stage='setup';party.soupId=null;party.soupUsed=[];party.soupHints=0;party.soupAnswerVisible=false;renderGame();
 });$('rtAccept').textContent='重新开局';
}
function renderSoupGame(box){
 const g=party,item=soupCurrent(),left=soupAvailable().length;
 let html=`<div class="gamebox hb-soup-game"><div class="hb-soup-heading"><h2>海龟汤</h2><button class="hb-truth-reset" onclick="resetSoupGame()" aria-label="重新开始海龟汤">${hbIcon('reset')}<span>重开</span></button></div>`;
 if(g.stage==='setup'){
  html+=`<div class="hb-soup-welcome">${hbArt('soup')}<h3>一个汤面，藏着另一种可能</h3></div><ol class="hb-soup-rules"><li>一人主持，其他人只看汤面，用提问还原故事。</li><li>主持人看汤底，回答“是／不是／不重要／无法确定”。</li><li>卡住时逐条看提示，讨论结束后再揭晓答案。</li></ol><label class="hb-soup-level" for="soupDifficulty">这次想玩哪种难度？<select id="soupDifficulty" onchange="setSoupDifficulty(this.value)">${Object.entries(SOUP_LEVELS).map(([key,label])=>`<option value="${key}" ${g.soupDifficulty===key?'selected':''}>${label}</option>`).join('')}</select></label><p class="hint">题库共 ${soupCases().length} 题，当前可抽 ${left} 题。本轮换题不会重复。</p><button class="primary" onclick="startSoupGame()">开始一锅汤</button>`;
 }else if(item){
  html+=`<div class="hb-soup-meta"><span class="hb-soup-tag">${SOUP_LEVELS[item.difficulty]}</span><small>本轮第 ${g.soupUsed.length} 题</small></div><h3 class="hb-soup-title">${escapeHtml(item.title)}</h3><article class="hb-soup-surface"><span>汤面 · 给玩家看的故事</span><p>${escapeHtml(item.surface)}</p></article>
  <button class="hb-soup-host-button" onclick="showSoupHost()">${hbIcon('user')}<span>主持人查看汤底</span>${hbIcon('chevron')}</button>
  ${g.soupHints?`<div class="hb-soup-hints"><h4>已经得到的提示</h4><ol>${item.hints.slice(0,g.soupHints).map(h=>`<li>${escapeHtml(h)}</li>`).join('')}</ol></div>`:''}
  ${g.soupAnswerVisible?`<article class="hb-soup-answer" role="status"><span class="hb-soup-tag">汤底 · 答案已揭晓</span><p>${escapeHtml(item.solution)}</p><ul>${item.facts.map(f=>`<li>${escapeHtml(f)}</li>`).join('')}</ul></article>`:''}
  <div class="hb-soup-actions"><button class="secondary" onclick="showSoupHint()" ${g.soupHints>=item.hints.length||g.soupAnswerVisible?'disabled':''}>${g.soupHints>=item.hints.length?'提示已全部展开':'给个提示 '+g.soupHints+'/'+item.hints.length}</button><button class="secondary" onclick="revealSoupAnswer()" ${g.soupAnswerVisible?'disabled':''}>${g.soupAnswerVisible?'已揭晓':'揭晓汤底'}</button></div><button class="primary" onclick="nextSoupCase()" ${left?'':'disabled'}>下一题</button><p class="hb-soup-progress">${left?'当前难度还剩 '+left+' 题未玩过。':'这一组已玩完，点击右上角“重开”开始新一轮。'}</p><p class="hb-soup-note">汤底仅在主持人确认查看或大家确认揭晓后显示。用现有线索大胆提问，也欢迎讨论其他合理解释。</p>`;
 }
 box.innerHTML=html+'</div>';
}
