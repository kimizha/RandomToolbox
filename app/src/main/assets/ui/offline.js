/* Local release: no authentication, SDK, cloud requests or storage migration. */
(()=>{
 const panel=document.createElement('div');panel.className='panel';
 panel.innerHTML='<h2 style="font-size:17px">本机数据</h2><p class="hint">收藏、转盘、设置与账目保存在本机。覆盖安装请保持相同签名，不要先卸载。仅云端保存且未下载的数据不在本机备份内。</p><button class="secondary" data-rt-backup-export onclick="rtExportLocalBackup()">导出本机 JSON 备份</button>';
 document.getElementById('settings').appendChild(panel);
 const tracks=["ACN Music. - Fooling Mode (1).mp3", "Kevin MacLeod - Fluffing a Duck.mp3", "NewPiano - tricks and traps.mp3", "Raphaël Beau - Micmacs à la gare.mp3", "SIDNEY JOSEPH BECHET - Si tu vois ma mère.mp3", "Ugress - Undead Funeral March.mp3"];
 const music=document.createElement('div');music.className='panel';
 music.innerHTML='<h2 style="font-size:17px">随身音乐</h2><label>内置曲目<select id="offlineTrack" style="width:100%;margin:12px 0"></select></label><audio id="offlineMusic" controls preload="none" style="width:100%"></audio><label class="setting">音乐音量<input id="musicVolume" type="range" min="0" max="100"></label>';
 document.getElementById('settings').appendChild(music);
 const select=document.getElementById('offlineTrack'),audio=document.getElementById('offlineMusic'),volume=document.getElementById('musicVolume');
 tracks.forEach((name,i)=>{const o=document.createElement('option');o.value=i;o.textContent=name.replace(/\.mp3$/i,'');select.appendChild(o)});
 select.value=String(Math.max(0,Math.min(tracks.length-1,Number(get('musicTrack',0))||0)));
 const load=()=>audio.src='music/'+encodeURIComponent(tracks[Number(select.value)]);
 load();select.onchange=()=>{const playing=!audio.paused;save('musicTrack',Number(select.value));load();if(playing)audio.play().catch(()=>toast('请点击播放'))};
 volume.value=String(Math.max(0,Math.min(100,Number(get('musicVolume',65)))));audio.volume=Number(volume.value)/100;
 volume.oninput=()=>{audio.volume=Number(volume.value)/100;save('musicVolume',Number(volume.value))};
})();
