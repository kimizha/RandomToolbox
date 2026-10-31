/* Pure offline rules. Amounts are integer hundredths; no account or network access. */
(function(root){
 'use strict';
 const LIMIT=100000000000;
 const unique=items=>[...new Set(items.map(x=>String(x).trim()).filter(Boolean))];
 function bomb(min,max,random){
  if(!Number.isSafeInteger(min)||!Number.isSafeInteger(max)||min>=max||max-min>1000000||Math.abs(min)>1000000000||Math.abs(max)>1000000000)throw Error('请填写有效整数范围，至少包含两个数，跨度不超过一百万');
  return {min,max,low:min,high:max,secret:random(min,max),ended:false,history:[]};
 }
 function guess(g,value){
  if(g.ended)throw Error('本局已经结束');
  if(!Number.isSafeInteger(value)||value<g.low||value>g.high)throw Error('请输入当前范围内的整数');
  const hit=value===g.secret;
  g.history.push({value,hit,low:g.low,high:g.high});
  if(hit)g.ended=true;else if(value<g.secret)g.low=value+1;else g.high=value-1;
  return hit;
 }
 function amount(text){
  if(!/^[+-]?\d{1,9}(\.\d{1,2})?$/.test(String(text).trim()))throw Error('请输入有效数值，最多两位小数');
  const n=Math.round(Number(text)*100);
  if(!Number.isSafeInteger(n)||!n||Math.abs(n)>LIMIT)throw Error('数值必须大于零且在允许范围内');return n;
 }
 function ledgerEntry(board,{id,at,player,to,delta,note=''}){
  if(board.closed)throw Error('历史场次已封存，请新建一局');
  const valid=p=>board.players.some(x=>x.id===p&&!x.archived);
  if(!valid(player)||!Number.isSafeInteger(delta)||!delta||Math.abs(delta)>LIMIT)throw Error('请选择有效玩家和数值');
  let legs=[{player,amount:delta}];
  if(board.mode==='transfer'){
   if(!valid(to)||to===player||delta<0)throw Error('请选择两位不同玩家，转移数值须大于零');
   legs=[{player,amount:-delta},{player:to,amount:delta}];
  }
  return {id,at,note:String(note).trim().slice(0,120),legs};
 }
 function totals(board){const out=Object.fromEntries(board.players.map(p=>[p.id,0]));for(const e of board.entries)for(const l of e.legs){if(!(l.player in out)||!Number.isSafeInteger(l.amount))throw Error('流水数据不完整');out[l.player]+=l.amount;if(!Number.isSafeInteger(out[l.player])||Math.abs(out[l.player])>LIMIT*100)throw Error('累计数值过大')}return out}
 function validateStore(d){
  if(!d||d.version!==1||!Array.isArray(d.boards)||!Array.isArray(d.results)||!d.custom||typeof d.custom!=='object')throw Error('本地玩法数据格式异常，原始数据已保留');
  for(const key of ['charades','truth','dare'])if(d.custom[key]!==undefined&&(!Array.isArray(d.custom[key])||d.custom[key].some(x=>typeof x!=='string'||x.length>80)))throw Error('本地自定义题库异常');
  for(const r of d.results)if(!r||!Array.isArray(r.right)||!Array.isArray(r.skipped)||!Number.isFinite(r.at))throw Error('本地成绩数据异常');
  for(const b of d.boards){
   if(!b||!['independent','transfer'].includes(b.mode)||!Array.isArray(b.players)||!Array.isArray(b.entries)||b.players.length<2||!b.id||!b.title)throw Error('本地记分局数据异常');
   if(new Set(b.players.map(p=>p.id)).size!==b.players.length||b.players.some(p=>typeof p.name!=='string'))throw Error('本地玩家数据异常');
   if(new Set(b.entries.map(e=>e.id)).size!==b.entries.length)throw Error('流水编号重复');
   for(const e of b.entries){if(!e.id||!Number.isFinite(e.at)||!Array.isArray(e.legs)||!e.legs.length)throw Error('本地流水异常');if(e.legs.some(l=>!l.amount||!Number.isSafeInteger(l.amount)||Math.abs(l.amount)>LIMIT)||b.mode==='independent'&&e.legs.length!==1)throw Error('流水数值异常');if(b.mode==='transfer'&&(e.legs.length!==2||e.legs[0].player===e.legs[1].player||e.legs.reduce((s,l)=>s+l.amount,0)!==0))throw Error('转移流水不平衡')}
   totals(b);
  }return d;
 }
 root.HBPartyCore={unique,bomb,guess,amount,ledgerEntry,totals,validateStore};
 if(typeof module!=='undefined')module.exports=root.HBPartyCore;
})(typeof window==='undefined'?globalThis:window);
