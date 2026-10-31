/* Device-only score sessions. Balanced transfers are one indivisible journal entry. */
(function(){
 'use strict';
 const C=window.HBPartyCore;
 const P=()=>window.HBParty,e=x=>P().e(x),state=()=>P().active;
 const board=()=>P().data.boards.find(b=>b.id===state()?.boardId);
 const b=(text,action,kind='secondary',disabled=false)=>`<button class="${kind}" onclick="HBScore.${action}" ${disabled?'disabled':''}>${text}</button>`;
 const fmt=n=>(n>0?'+':n<0?'−':'')+(Math.abs(n)/100).toLocaleString('zh-CN',{maximumFractionDigits:2});
 const name=(g,id)=>g.players.find(p=>p.id===id)?.name||'未知玩家';
 function mutate(change,undoable=true){
  const id=state()?.boardId;if(!id)return false;
  return P().commit(d=>{const g=d.boards.find(x=>x.id===id);if(!g||g.closed)throw Error('历史场次已封存');if(undoable)g.undo={players:JSON.parse(JSON.stringify(g.players)),entries:JSON.parse(JSON.stringify(g.entries))};change(g);C.totals(g)});
 }
 function done(ok){if(ok){P().redraw();toast('已保存到本机');sfx('paper');vibrate(20)}return ok}
 function create(){
  P().modal('新建记分局',`<label>场次名称<input id="hsTitle" maxlength="40" value="朋友的一局"></label><div class="hp-two"><label>记分方式<select id="hsMode"><option value="independent">独立记分</option><option value="transfer">玩家间转移 · 总和为零</option></select></label><label>显示单位<select id="hsUnit"><option value="分">积分</option><option value="元">金额（仅记录）</option></select></label></div><label>玩家姓名 · 每行一位（2～12 人）<textarea id="hsPlayers" rows="4" placeholder="小开心&#10;小幸运">玩家 1\n玩家 2</textarea></label><p class="hint">独立记分：分别加减。玩家间转移：一人减少、一人增加，同一笔自动配平。本工具仅做本地记录。</p>`,()=>{
   const title=$('hsTitle').value.trim(),players=P().lines($('hsPlayers').value,2,12);if(!title)throw Error('请填写场次名称');if(players.some(n=>n.length>20))throw Error('玩家姓名最多 20 字');
   const id=P().uid(),mode=$('hsMode').value,unit=$('hsUnit').value;
   if(!P().commit(d=>{if(d.boards.length>=100)throw Error('已保存 100 场，请先删除不需要的历史场次');d.boards.unshift({id,title,mode,unit,created:Date.now(),closed:false,players:players.map(n=>({id:P().uid(),name:n,archived:false})),entries:[],undo:null})}))return false;
   state().boardId=id;state().page='board';P().setStage('play');P().redraw();toast('已创建');
  },'开始记分');
 }
 function select(id){if(!P().data.boards.some(x=>x.id===id))return;state().boardId=id;state().page='board';P().setStage('play');P().redraw()}
 function list(){state().page='list';state().boardId=null;P().setStage('setup');P().redraw()}
 function playerOptions(g,current,includeArchived=false){return g.players.filter(p=>includeArchived||!p.archived).map(p=>`<option value="${e(p.id)}" ${p.id===current?'selected':''}>${e(p.name)}${p.archived?'（已移除）':''}</option>`).join('')}
 function editPlayer(id){
  const g=board(),p=g?.players.find(p=>p.id===id);if(!g||g.closed||!p||p.archived)return;
  P().modal('修改玩家名称',`<label>名称<input id="hsName" maxlength="20" value="${e(p.name)}"></label>`,()=>{const value=$('hsName').value.trim();if(!value)throw Error('请填写名称');if(g.players.some(x=>x.id!==id&&!x.archived&&x.name===value))throw Error('已有同名玩家');return done(mutate(d=>d.players.find(x=>x.id===id).name=value))});
 }
 function addPlayer(){
  const g=board();if(!g||g.closed)return;if(g.players.filter(p=>!p.archived).length>=12)return toast('每局最多 12 位在场玩家');
  P().modal('添加玩家','<label>玩家名称<input id="hsName" maxlength="20" placeholder="输入姓名"></label>',()=>{const value=$('hsName').value.trim();if(!value)throw Error('请填写名称');if(g.players.some(x=>!x.archived&&x.name===value))throw Error('已有同名玩家');return done(mutate(d=>d.players.push({id:P().uid(),name:value,archived:false})))});
 }
 function removePlayer(id){const g=board(),p=g?.players.find(x=>x.id===id);if(!g||g.closed||!p||p.archived)return;if(g.players.filter(x=>!x.archived).length<=2)return toast('每局至少保留 2 位玩家');
  rtDialog('移除 '+p.name+'？','该玩家将移出记分区，已有流水和累计结果保留在本局中，保证历史账目完整。',()=>done(mutate(d=>d.players.find(x=>x.id===id).archived=true)));
 }
 function amountDialog(id,sign=1,editing=null){
  const g=board();if(!g||g.closed)return;const old=editing?g.entries.find(x=>x.id===editing):null;if(editing&&!old)return;
  const transfer=g.mode==='transfer',from=old?.legs[0].player||id||g.players.find(x=>!x.archived)?.id,to=old?.legs[1]?.player||g.players.find(x=>!x.archived&&x.id!==from)?.id;
  const delta=old?(transfer?old.legs[1].amount:old.legs[0].amount):(transfer?1000:sign*1000);
  const players=transfer?`<div class="hp-two"><label>减少的一方<select id="hsFrom">${playerOptions(g,from,!!old)}</select></label><label>增加的一方<select id="hsTo">${playerOptions(g,to,!!old)}</select></label></div>`:`<label>玩家<select id="hsFrom">${playerOptions(g,from,!!old)}</select></label>`;
  P().modal(old?'修改这笔记录':transfer?'玩家间转移':sign>0?'加分':'减分',players+`<label>${transfer?'转移数值（正数）':'增减数值（负号代表减少）'}<input id="hsAmount" type="number" inputmode="decimal" step="0.01" value="${delta/100}"></label><div class="hp-quick">${(transfer?[10,20,50,100]:[10,20,50,100,-10,-20,-50,-100]).map(n=>b((n>0?'+':'')+n,`fill(${n})`)).join('')}</div><label>备注（可选）<input id="hsNote" maxlength="120" value="${e(old?.note||'')}" placeholder="如：第 2 轮"></label><p class="hint">${transfer?'保存时生成同一笔配平流水，任何修改和删除都会同时处理双方。':'最多两位小数，保存后立即更新累计。'}</p>`,()=>{
   const player=$('hsFrom').value,target=$('hsTo')?.value,delta=C.amount($('hsAmount').value),note=$('hsNote').value;
   // Editing historical entries may reference removed players. They remain part of the ledger.
   const inputBoard=old?{...g,players:g.players.map(p=>({...p,archived:false}))}:g;
   const entry=C.ledgerEntry(inputBoard,{id:old?.id||P().uid(),at:old?.at||Date.now(),player,to:target,delta,note});
   return done(mutate(d=>{if(old){const i=d.entries.findIndex(x=>x.id===old.id);if(i<0)throw Error('记录不存在');d.entries[i]=entry}else{if(d.entries.length>=5000)throw Error('本局记录已达 5000 笔，请保存后新建一局');d.entries.push(entry)}}));
  },old?'保存修改':'确认记入');
 }
 function fill(n){$('hsAmount').value=n;vibrate(12)}
 function ledger(){if(!board())return;state().page='ledger';P().redraw()}
 function showBoard(){state().page='board';P().redraw()}
 function editEntry(id){amountDialog(null,1,id)}
 function deleteEntry(id){const g=board();if(!g||g.closed||!g.entries.some(x=>x.id===id))return;rtDialog('删除这笔记录？',g.mode==='transfer'?'双方数值会同时撤回，本局仍保持平衡。':'累计结果会随之重新计算。',()=>done(mutate(d=>d.entries=d.entries.filter(x=>x.id!==id))))}
 function undo(){const g=board();if(!g||g.closed||!g.undo)return;rtDialog('撤销上一步操作？','将恢复上一步之前的玩家与流水。此操作本身不能再次撤销。',()=>done(mutate(d=>{const prev=d.undo;if(!prev)throw Error('没有可撤销的操作');d.players=prev.players;d.entries=prev.entries;d.undo=null},false)))}
 function clear(){const g=board();if(!g||g.closed)return;const id=g.id;rtDialog('清空本局全部记录？','玩家会保留，所有累计将归零。',()=>rtDialog('再次确认清空','请确认正在清空的是“'+g.title+'”。清空后可用“撤销上一步”恢复一次。',()=>{if(board()?.id===id)done(mutate(d=>d.entries=[]))}))}
 function close(){const g=board();if(!g||g.closed)return;rtDialog('保存为历史场次？','本局将封存为只读记录，之后可以新建另一局。',()=>{if(mutate(d=>{d.closed=true;d.undo=null},false)){list();toast('历史场次已保存')}})}
 function deleteBoard(id){const g=P().data.boards.find(x=>x.id===id);if(!g)return;rtDialog('删除这场记分局？','“'+g.title+'”及其全部流水将从本机删除，无法恢复。',()=>{if(P().commit(d=>d.boards=d.boards.filter(x=>x.id!==id))){list();toast('已删除')}})}
 function clearAll(){rtDialog('清除所有本地记分数据？','包括正在记录和已经封存的所有场次。不会影响其他玩法。',()=>rtDialog('再次确认永久删除','所有记分场次与流水将被永久删除，此操作不能撤销。',()=>{if(P().commit(d=>d.boards=[])){list();toast('记分数据已清除')}}))}
 function render(box){
  const s=state(),g=board();let html=P().header('score','本地记录积分或金额，支持独立记分与玩家间平衡转移。账目不会上传账号云端。');
  if(P().readError)html+=`<p class="hp-error" role="alert">${e(P().readError)}</p>`;
  if(s.page==='list'||!g){
   html+=b('新建记分局','create()','primary');
   html+=`<div class="hp-sessions">${P().data.boards.length?P().data.boards.map(x=>`<article class="hp-session"><button onclick="HBScore.select('${e(x.id)}')"><strong>${e(x.title)}</strong><small>${x.closed?'已封存':'进行中'} · ${x.players.filter(p=>!p.archived).length} 人 · ${x.entries.length} 笔 · ${x.mode==='transfer'?'平衡转移':'独立记分'}</small><small>${new Date(x.created).toLocaleString()}</small></button>${b('删除',`deleteBoard('${e(x.id)}')`,'hp-small')}</article>`).join(''):'<div class="hp-private"><span>'+hbIcon('plus')+'</span><h3>从大家的名字开始</h3><p>关闭 App 后仍可查看。清除 App 数据或卸载会删除本地账目。</p></div>'}</div>`;
   if(P().data.boards.length)html+=b('清除所有记分场次','clearAll()');
  }else if(s.page==='ledger'){
   html+=`<div class="hp-heading"><h3>${e(g.title)} · 详细流水</h3>${b('返回记分','showBoard()','hp-small')}</div><div class="hp-ledger">${g.entries.length?[...g.entries].reverse().map(x=>`<article><div class="hp-ledger-lines">${x.legs.map(l=>`<p><strong>${e(name(g,l.player))}</strong><span class="${l.amount<0?'hp-negative':'hp-positive'}">${fmt(l.amount)} ${e(g.unit)}</span></p>`).join('')}</div><small>${new Date(x.at).toLocaleString()}${x.note?' · '+e(x.note):''}</small>${g.closed?'':`<div class="hp-two">${b('修改',`editEntry('${e(x.id)}')`,'hp-small')}${b('删除',`deleteEntry('${e(x.id)}')`,'hp-small')}</div>`}</article>`).join(''):'<p class="hint">还没有记录，返回记分区添加第一笔。</p>'}</div>`;
  }else{
   const total=C.totals(g),sum=Object.values(total).reduce((a,b)=>a+b,0);
   html+=`<div class="hp-heading"><div><h3>${e(g.title)}</h3><small>${g.closed?'历史场次 · 只读':g.mode==='transfer'?'玩家间转移 · 双方自动配平':'独立记分 · 累计分别计算'}</small></div>${b('场次','list()','hp-small')}</div>`;
   if(g.mode==='transfer')html+=`<p class="hp-balance">所有玩家合计 ${fmt(sum)} ${e(g.unit)} · ${sum===0?'账目平衡':'请检查记录'}</p>`;
   html+=`<div class="hp-score-players">${g.players.filter(p=>!p.archived).map(p=>`<article class="hp-score-card"><div class="hp-player-title"><button class="hp-name" onclick="HBScore.editPlayer('${e(p.id)}')" ${g.closed?'disabled':''}>${e(p.name)}${g.closed?'':hbIcon('edit')}</button>${g.closed?'':b('移除',`removePlayer('${e(p.id)}')`,'hp-small')}</div><strong class="hp-total ${total[p.id]<0?'hp-negative':'hp-positive'}">${fmt(total[p.id])}<small>${e(g.unit)}</small></strong>${g.closed?'':`<div class="hp-two">${b(g.mode==='transfer'?'付出':'− 减分',`amountDialog('${e(p.id)}',-1)`)}${b(g.mode==='transfer'?'转移记分':'+ 加分',`amountDialog('${e(p.id)}',1)`,'primary')}</div>`}</article>`).join('')}</div>`;
   if(g.players.some(p=>p.archived))html+=`<details class="hp-records"><summary>已移除玩家 · 历史累计保留</summary>${g.players.filter(p=>p.archived).map(p=>`<p>${e(p.name)}：${fmt(total[p.id])} ${e(g.unit)}</p>`).join('')}</details>`;
   html+=`<div class="hp-two">${b('详细流水（'+g.entries.length+'）','ledger()')}${g.closed?'':b('撤销上一步','undo()','secondary',!g.undo)}</div>`;
   if(!g.closed)html+=`<div class="hp-two">${b('添加玩家','addPlayer()')}${b('清空本局记录','clear()')}</div>${b('结束并保存历史','close()','primary')}`;
   else html+=b('新建另一局','create()','primary');
  }
  box.innerHTML='<div class="gamebox hp-game hp-score">'+html+'</div>';
 }
 window.HBScore={render,create,select,list,editPlayer,addPlayer,removePlayer,amountDialog,fill,ledger,showBoard,editEntry,deleteEntry,undo,clear,close,deleteBoard,clearAll};
})();
