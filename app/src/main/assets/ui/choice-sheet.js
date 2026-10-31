/* Custom single-select surface. Native select values/events remain the source of truth. */
(function(){
 'use strict';let current=null;const buttons=new WeakMap();
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function title(select){return select.getAttribute('aria-label')||[...(select.closest('label')?.childNodes||[])].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ')||document.querySelector(`label[for="${select.id}"]`)?.childNodes[0]?.textContent.trim()||'请选择'}
 function update(select){const b=buttons.get(select);if(!b)return;b.disabled=select.disabled;b.setAttribute('aria-label',title(select)+'：'+(select.selectedOptions[0]?.textContent||'请选择'));b.querySelector('strong').textContent=select.selectedOptions[0]?.textContent||'请选择'}
 function close(){if(!current)return false;const c=current;current=null;document.body.classList.remove('hb-choice-open');c.shade.remove();c.button.setAttribute('aria-expanded','false');if(c.button.isConnected)c.button.focus({preventScroll:true});return true}
 function open(select){
  if(select.disabled)return;close();const b=buttons.get(select),shade=document.createElement('div');shade.id='hbChoiceShade';shade.className='hb-choice-shade';
  shade.innerHTML=`<section class="hb-choice-sheet" role="dialog" aria-modal="true" aria-label="${esc(title(select))}"><span class="hb-sheet-handle"></span><header><div><small>轻松选一下</small><h3>${esc(title(select))}</h3></div><button type="button" class="hb-choice-close" aria-label="关闭选择">${hbIcon('back')}</button></header><div class="hb-choice-options" role="listbox" aria-label="${esc(title(select))}">${[...select.options].map((o,i)=>`<button type="button" role="option" class="hb-choice-option ${o.selected?'selected':''}" aria-selected="${o.selected}" data-index="${i}" ${o.disabled||o.parentElement.disabled?'disabled':''}><span>${esc(o.textContent)}</span><i>${o.selected?hbIcon('check'):''}</i></button>`).join('')}</div><p>点击选项立即应用，返回可取消。</p></section>`;
  document.body.appendChild(shade);document.body.classList.add('hb-choice-open');shade.addEventListener('touchmove',ev=>{if(!ev.target.closest('.hb-choice-options'))ev.preventDefault()},{passive:false});current={select,button:b,shade};b.setAttribute('aria-expanded','true');
  shade.querySelector('.hb-choice-close').onclick=close;shade.onclick=ev=>{if(ev.target===shade)close()};
  shade.querySelectorAll('[data-index]').forEach(option=>option.onclick=()=>{if(!select.isConnected){close();return}const i=Number(option.dataset.index);close();select.selectedIndex=i;update(select);select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}))});
  shade.querySelector('[aria-selected="true"]')?.focus({preventScroll:true});
 }
 function enhance(root=document){
  if(current&&(!current.select.isConnected||current.select.closest('.view')&&!current.select.closest('.view').classList.contains('active')))close();
  root.querySelectorAll('select').forEach(select=>{
   if(select.multiple)return;
   let b=buttons.get(select);
   if(!b){b=document.createElement('button');b.type='button';b.className='hb-choice-trigger';b.setAttribute('aria-haspopup','listbox');b.setAttribute('aria-expanded','false');b.innerHTML='<strong></strong>'+hbIcon('chevron');buttons.set(select,b);select.classList.add('hb-native-select');select.setAttribute('aria-hidden','true');select.tabIndex=-1;select.insertAdjacentElement('afterend',b);b.onclick=ev=>{ev.preventDefault();open(select)};select.addEventListener('change',()=>update(select))}
   const text=select.selectedOptions[0]?.textContent||'请选择';if(b.querySelector('strong').textContent!==text||b.disabled!==select.disabled)update(select);
  });
 }
 document.addEventListener('keydown',ev=>{if(!current)return;if(ev.key==='Escape'){ev.preventDefault();close()}else if(ev.key==='Tab'){const all=[...current.shade.querySelectorAll('button:not(:disabled)')],i=all.indexOf(document.activeElement);ev.preventDefault();all[(i+(ev.shiftKey?-1:1)+all.length)%all.length]?.focus()}else if(['ArrowDown','ArrowUp','Home','End'].includes(ev.key)){const all=[...current.shade.querySelectorAll('[role="option"]:not(:disabled)')],i=all.indexOf(document.activeElement);ev.preventDefault();all[ev.key==='Home'?0:ev.key==='End'?all.length-1:(i+(ev.key==='ArrowUp'?-1:1)+all.length)%all.length]?.focus()}});
 document.addEventListener('DOMContentLoaded',()=>{enhance();let queued=false;new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;enhance()})}).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['disabled','selected']})});
 window.HBChoice={close,enhance,open};
})();
