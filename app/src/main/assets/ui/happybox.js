/* Presentation helpers only. No authentication, randomness or persistence changes. */
const hbPaths={reset:'M20 7v5h-5M20 12a8 8 0 1 0-2 5M20 12l-3-5',heart:'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z',bolt:'m13 2-9 12h7l-1 8L20 9h-7Z',home:'M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',grid:'M3 3h6v6H3z M15 3h6v6h-6z M3 15h6v6H3z M15 15h6v6h-6z',user:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',game:'M7 7h10c3 0 4 3 4 8s-3 6-6 1H9c-3 5-6 4-6-1S4 7 7 7ZM8 10v5M5.5 12.5h5M16 11h.1M18 14h.1',sliders:'M3 6h7m4 0h7M3 12h3m4 0h11M3 18h11m4 0h3M10 3v6M6 9v6m8 0v6',edit:'m4 16 12-12 4 4L8 20l-5 1Zm10-10 4 4',arrow:'M4 12h16m-6-6 6 6-6 6',chevron:'m9 5 7 7-7 7',star:'m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z',plus:'M12 4v16M4 12h16',play:'m8 5 11 7-11 7Z',pause:'M8 5v14M16 5v14',prev:'M5 5v14m14-14L7 12l12 7Z',next:'M19 5v14M5 5l12 7-12 7Z',back:'m15 5-7 7 7 7',check:'m5 12 4 4L19 6'};
function hbIcon(name){return `<svg class="hb-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="${hbPaths[name]||hbPaths.star}"/></svg>`}
const hbRects={coin:[12,45,380,335],wheel:[400,18,300,360],dice:[755,58,300,310],draw:[1100,35,345,340],number:[8,435,400,280],rps:[425,390,270,330],wolf:[735,390,360,335],spy:[1100,395,345,325],truth:[15,750,365,280],music:[380,730,350,340],idea:[748,730,320,335],settings:[1118,745,320,315]};
function hbArt(name){if(name==='score')return '<span class="hb-art art-score" aria-hidden="true"><svg viewBox="627 627 627 627"><image href="ui/party-icons.png" width="1254" height="1254"/></svg></span>';if(name==='soup')return '<span class="hb-art art-soup" aria-hidden="true"><img src="ui/soup-turtle.png" alt=""></span>';if(name==='coin')return `<span class="hb-art art-coin" aria-hidden="true">${hbGameArt('heads')}</span>`;const r=hbRects[name]||hbRects.idea;return `<span class="hb-art art-${name}" aria-hidden="true"><svg viewBox="${r.join(' ')}"><defs><clipPath id="hb-clip-${name}"><rect x="${r[0]}" y="${r[1]}" width="${r[2]}" height="${r[3]}"/></clipPath></defs><image href="ui/toolkit.png" width="1448" height="1086" clip-path="url(#hb-clip-${name})"/></svg></span>`}
// Every hand uses the same raster atlas, avoiding WebView-specific SVG gradient rendering.
const hbGameRects={rock:[65,100,435,440],scissors:[550,20,440,520],paper:[1030,16,500,524],heads:[32,23,823,825],tails:[913,23,819,825]};
function hbGameArt(name){const r=hbGameRects[name],coin=name==='heads'||name==='tails';return `<span class="hb-game-art" role="img" aria-label="${{rock:'石头',scissors:'剪刀',paper:'布',heads:'正面',tails:'反面'}[name]}"><svg viewBox="${r.join(' ')}"><defs><clipPath id="hb-game-${name}"><rect x="${r[0]}" y="${r[1]}" width="${r[2]}" height="${r[3]}"/></clipPath></defs><image href="ui/${coin?'coin-faces':'game-pieces'}.png" width="${coin?1774:1536}" height="${coin?887:1024}" clip-path="url(#hb-game-${name})"/></svg></span>`}
function hbHand(name){return hbGameArt(({石头:'rock',剪刀:'scissors',布:'paper'})[name]||'rock')}
// Short broadband contact transient plus inharmonic modes, rather than musical notification notes.
function hbCoinSound(type,strength=1){
 const c=soundReady();if(!c)return;
 const t=c.currentTime+.008,impact=type==='coinImpact',level=Math.max(0,Math.min(1,strength))*settings.volume/100;
 const master=c.createGain();master.gain.value=level;master.connect(c.destination);
 const seconds=impact ? .032 : .018,buffer=c.createBuffer(1,Math.ceil(c.sampleRate*seconds),c.sampleRate),samples=buffer.getChannelData(0);
 let seed=7823;for(let i=0;i<samples.length;i++){seed=(Math.imul(seed,1664525)+1013904223)|0;samples[i]=(seed/2147483648)*Math.exp(-i/(samples.length*.18))}
 const noise=c.createBufferSource(),filter=c.createBiquadFilter(),contact=c.createGain();noise.buffer=buffer;filter.type='highpass';filter.frequency.value=impact?1800:3200;contact.gain.value=impact ? .16 : .065;
 noise.connect(filter);filter.connect(contact);contact.connect(master);noise.start(t);noise.onended=()=>{noise.disconnect();filter.disconnect();contact.disconnect()};
 const modes=impact?[[1820,.21,.065],[3070,.16,.035],[4510,.11,.024],[6740,.065,.012],[152,.045,.1]]:[[2600,.055,.025],[4270,.03,.015]];
 for(const [freq,length,volume] of modes){const o=c.createOscillator(),g=c.createGain();o.frequency.setValueAtTime(freq,t);o.frequency.exponentialRampToValueAtTime(freq*.985,t+length);g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(volume,t+.001);g.gain.exponentialRampToValueAtTime(.0001,t+length);o.connect(g);g.connect(master);o.start(t);o.stop(t+length+.01);o.onended=()=>{o.disconnect();g.disconnect()}}
 setTimeout(()=>master.disconnect(),500);
}
function hbPolish(root=document.body){
 root.querySelectorAll('[data-art],.hb-art:empty').forEach(el=>{const name=el.dataset.art||[...el.classList].find(c=>c.startsWith('art-'))?.slice(4);if(name)el.outerHTML=hbArt(name)});
 root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=hbIcon(el.dataset.icon);el.removeAttribute('data-icon')});
 const title=document.querySelector('#settings .top h1');if(title)title.textContent='我的开心盒';

}
document.addEventListener('DOMContentLoaded',()=>{hbPolish();let queued=false;const observer=new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;observer.disconnect();hbPolish();observer.observe(document.body,{childList:true,subtree:true,characterData:true})})});observer.observe(document.body,{childList:true,subtree:true,characterData:true});});
