/* Local release: no authentication, SDK, cloud requests or storage migration. */
(()=>{
 const panel=document.createElement('div');panel.className='panel';
 panel.innerHTML='<h2 style="font-size:17px">本机数据</h2><p class="hint">收藏、转盘、设置与账目保存在本机。覆盖安装请保持相同签名，不要先卸载。仅云端保存且未下载的数据不在本机备份内。</p><button class="secondary" data-rt-backup-export onclick="rtExportLocalBackup()">导出本机 JSON 备份</button>';
 document.getElementById('settings').appendChild(panel);
})();
