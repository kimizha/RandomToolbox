package com.randomtoolbox.app;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.content.Context;
import android.content.SharedPreferences;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Base64;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity implements SensorEventListener {
    private static final String HOME_URL = "file:///android_asset/index.html";
    private static final String MANIFEST_URL = "https://raw.githubusercontent.com/kimizha/RandomToolbox/main/updates/version.json";
    private static final String HTML_URL = "https://raw.githubusercontent.com/kimizha/RandomToolbox/main/updates/index.html";
    private static final int BUNDLED_WEB_VERSION = 12;
    private static final int MAX_HTML_BYTES = 2 * 1024 * 1024;

    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private WebView webView;
    private SharedPreferences prefs;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private float gravityX, gravityY, gravityZ;
    private boolean sensorReady = false;
    private long lastShake = 0;
    private volatile boolean checking = false;
    private boolean restoring = false;
    private boolean pagePrepared = false;
    private String statusText = "自动检查更新 · 支持离线使用";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(0xfff6f7fb);
        getWindow().setNavigationBarColor(0xfff6f7fb);
        prefs = getSharedPreferences("rt_native_update", MODE_PRIVATE);
        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        accelerometer = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        webView = new WebView(this);
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        webView.setWebChromeClient(new WebChromeClient());
        webView.addJavascriptInterface(new NativeBridge(), "RandomToolboxNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                if (!HOME_URL.equals(url) || pagePrepared) return;
                pagePrepared = true;
                injectFeatures();
                if (restoring) {
                    restoring = false;
                    updateStatus("已恢复内置网页版本 " + BUNDLED_WEB_VERSION);
                    return;
                }
                loadSavedWebUpdate();
                checkForUpdates(false);
            }
        });
        webView.loadUrl(HOME_URL);
    }

    private void js(String script) {
        main.post(() -> { if (webView != null) webView.evaluateJavascript(script, null); });
    }
    private void notifyUser(String message) {
        js("if(typeof toast==='function')toast(" + JSONObject.quote(message) + ");");
    }
    private File updateFile() { return new File(getFilesDir(), "randomtoolbox_update.html"); }
    private File updateHashFile() { return new File(getFilesDir(), "randomtoolbox_update.sha256"); }

    private void loadSavedWebUpdate() {
        worker.execute(() -> {
            File file = updateFile();
            if (!file.isFile()) return;
            try {
                byte[] bytes = readLimited(new FileInputStream(file), MAX_HTML_BYTES);
                File hashFile = updateHashFile();
                if (!hashFile.isFile()) throw new IOException("missing cache checksum");
                String expected = new String(readLimited(new FileInputStream(hashFile), 128), StandardCharsets.US_ASCII).trim();
                if (!sha256(bytes).equals(expected)) throw new IOException("cache checksum mismatch");
                String html = new String(bytes, StandardCharsets.UTF_8);
                if (!validHtml(html)) throw new IOException("invalid saved html");
                applyHtml(html);
            } catch (Exception e) {
                file.delete();
                updateHashFile().delete();
                prefs.edit().remove("webVersion").apply();
                updateStatus("本地更新缓存异常，已使用内置版本");
            }
        });
    }

    private boolean validHtml(String html) {
        return html.length() > 1000 && html.contains("<html") && html.contains("</html>") &&
            html.contains("随机工具箱") && html.contains("function openTool(") && html.contains("function go(");
    }

    private void applyHtml(String html) {
        String b64 = Base64.encodeToString(html.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
        // document.write 保留 file:///android_asset/ 的同源 localStorage。
        js("(function(){try{var b=Uint8Array.from(atob('" + b64 + "'),c=>c.charCodeAt(0));" +
           "var h=new TextDecoder('utf-8').decode(b);document.open();document.write(h);document.close();" +
           "setTimeout(function(){" + featureScript() + "},100);" +
           "}catch(e){console.error('网页更新应用失败',e);}})();");
    }

    private void injectFeatures() { js(featureScript()); }
    private String featureScript() {
        return """
            (function(){
              try {
                window.rtShake=function(){
                  try {
                    var s=JSON.parse(localStorage.getItem('rt_settings')||'{}');
                    if(s.shake===false || typeof busy==='undefined' || busy) return;
                    var tool=document.getElementById('tool');
                    if(!tool || !tool.classList.contains('active')) return;
                    var methods={coin:'flipCoin',number:'genNumber',wheel:'spinWheel',dice:'rollDice',rps:'playRps',draw:'drawOne'};
                    var name=methods[activeTool];
                    if(name && typeof window[name]==='function')window[name]();
                  }catch(e){console.warn(e);}
                };
                var settingsView=document.getElementById('settings');
                if(!settingsView)return;
                if(!document.getElementById('rtShakeRow')){
                  var panel=settingsView.querySelector('.panel');
                  if(panel){
                    var row=document.createElement('div');row.className='setting';row.id='rtShakeRow';
                    var label=document.createElement('span');label.textContent='📳 摇一摇触发';
                    var box=document.createElement('input');box.type='checkbox';box.id='rtShakeToggle';
                    var state=JSON.parse(localStorage.getItem('rt_settings')||'{}');
                    box.checked=state.shake!==false;
                    box.onchange=function(){
                      var st=JSON.parse(localStorage.getItem('rt_settings')||'{}');
                      st.shake=box.checked;
                      localStorage.setItem('rt_settings',JSON.stringify(st));
                      if(typeof settings!=='undefined')settings.shake=box.checked;
                    };
                    row.appendChild(label);row.appendChild(box);panel.appendChild(row);
                  }
                }
                if(!document.getElementById('rtUpdatePanel')){
                  var p=document.createElement('div');p.className='panel';p.id='rtUpdatePanel';
                  var title=document.createElement('h2');title.style.fontSize='17px';title.textContent='☁️ 云端更新';
                  var status=document.createElement('p');status.className='hint';status.id='rtUpdateStatus';
                  var check=document.createElement('button');check.className='secondary';
                  check.style.cssText='width:100%;margin-bottom:9px';check.textContent='检查更新';
                  check.onclick=function(){RandomToolboxNative.checkUpdate();};
                  var rollback=document.createElement('button');rollback.className='secondary';
                  rollback.style.width='100%';rollback.textContent='恢复内置版本';
                  rollback.onclick=function(){
                    if(confirm('恢复内置版本？当前已下载的网页更新将被移除。'))RandomToolboxNative.rollback();
                  };
                  p.appendChild(title);p.appendChild(status);p.appendChild(check);p.appendChild(rollback);
                  settingsView.appendChild(p);
                }
                var status=document.getElementById('rtUpdateStatus');
                if(status)status.textContent=__STATUS__;
              }catch(e){console.error('原生功能注入失败',e);}
            })();
            """.replace("__STATUS__", JSONObject.quote(statusText));
    }
    private void updateStatus(String message) {
        statusText = message;
        js("var e=document.getElementById('rtUpdateStatus');if(e)e.textContent=" + JSONObject.quote(message) + ";");
    }

    private void checkForUpdates(boolean manual) {
        if (checking) { if (manual) updateStatus("正在检查更新，请稍候…"); return; }
        checking = true;
        if (manual) updateStatus("正在检查更新…");
        worker.execute(() -> {
            try {
                JSONObject manifest = new JSONObject(new String(download(MANIFEST_URL, 32768), StandardCharsets.UTF_8));
                int version = manifest.getInt("webVersion");
                String hash = manifest.getString("sha256").toLowerCase(Locale.ROOT);
                if (!hash.matches("[a-f0-9]{64}")) throw new IOException("invalid sha256");
                int installed = prefs.getInt("webVersion", BUNDLED_WEB_VERSION);
                int blocked = prefs.getInt("blockedVersion", -1);
                if (version <= installed) {
                    if (manual) updateStatus("当前已是最新网页版本 " + installed);
                    return;
                }
                if (version == blocked) {
                    if (manual) updateStatus("该网页版本已手动回退，等待后续新版本");
                    return;
                }
                updateStatus("发现网页版本 " + version + "，正在下载…");
                byte[] bytes = download(HTML_URL, MAX_HTML_BYTES);
                if (!sha256(bytes).equals(hash)) throw new IOException("SHA-256 mismatch");
                String html = new String(bytes, StandardCharsets.UTF_8);
                if (!validHtml(html)) throw new IOException("invalid HTML");
                File tmp = new File(getFilesDir(), "randomtoolbox_update.tmp");
                File hashTmp = new File(getFilesDir(), "randomtoolbox_update.sha256.tmp");
                try (FileOutputStream out = new FileOutputStream(tmp)) {
                    out.write(bytes);out.getFD().sync();
                }
                try (FileOutputStream out = new FileOutputStream(hashTmp)) {
                    out.write(hash.getBytes(StandardCharsets.US_ASCII));out.getFD().sync();
                }
                File dest = updateFile(), hashDest = updateHashFile();
                if (dest.exists() && !dest.delete()) throw new IOException("cannot replace cached HTML");
                if (!tmp.renameTo(dest)) throw new IOException("cannot save cached HTML");
                if (hashDest.exists() && !hashDest.delete()) throw new IOException("cannot replace checksum");
                if (!hashTmp.renameTo(hashDest)) throw new IOException("cannot save checksum");
                prefs.edit().putInt("webVersion", version).apply();
                updateStatus("已下载网页版本 " + version + "，正在应用…");
                applyHtml(html);
                main.postDelayed(() -> notifyUser("已更新到网页版本 " + version), 700);
            } catch (Exception e) {
                if (manual) updateStatus("更新失败：" + e.getMessage());
            } finally { checking = false; }
        });
    }

    private static byte[] download(String address, int maxBytes) throws IOException {
        HttpURLConnection conn = (HttpURLConnection) new URL(address).openConnection();
        conn.setConnectTimeout(9000);
        conn.setReadTimeout(12000);
        conn.setInstanceFollowRedirects(true);
        try {
            if (conn.getResponseCode() != 200) throw new IOException("HTTP " + conn.getResponseCode());
            return readLimited(conn.getInputStream(), maxBytes);
        } finally { conn.disconnect(); }
    }
    private static byte[] readLimited(InputStream input, int max) throws IOException {
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192];int n,total=0;
            while ((n=in.read(buf))!=-1) {
                total+=n;
                if(total>max)throw new IOException("文件超过大小限制");
                out.write(buf,0,n);
            }
            return out.toByteArray();
        }
    }
    private static String sha256(byte[] data) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder b = new StringBuilder();
        for(byte x:digest)b.append(String.format(Locale.ROOT,"%02x",x&255));
        return b.toString();
    }

    public class NativeBridge {
        @JavascriptInterface public void checkUpdate() { main.post(() -> checkForUpdates(true)); }
        @JavascriptInterface public void rollback() {
            main.post(() -> {
                // 不直接中断后台下载：先排队，确保回退不会被正在执行的更新覆盖。
                worker.execute(() -> {
                    int v = prefs.getInt("webVersion", BUNDLED_WEB_VERSION);
                    prefs.edit().putInt("blockedVersion", v).remove("webVersion").commit();
                    updateFile().delete();updateHashFile().delete();
                    main.post(() -> {
                        restoring = true;
                        pagePrepared = false;
                        webView.loadUrl(HOME_URL);
                    });
                });
            });
        }
    }

    @Override protected void onResume() {
        super.onResume();sensorReady=false;
        if(sensorManager!=null && accelerometer!=null)
            sensorManager.registerListener(this,accelerometer,SensorManager.SENSOR_DELAY_GAME);
        if(webView!=null)webView.onResume();
    }
    @Override protected void onPause() {
        if(sensorManager!=null)sensorManager.unregisterListener(this);
        if(webView!=null)webView.onPause();
        super.onPause();
    }
    @Override public void onSensorChanged(SensorEvent e) {
        if(e.sensor.getType()!=Sensor.TYPE_ACCELEROMETER || webView==null)return;
        float a=.82f;
        if(!sensorReady){gravityX=e.values[0];gravityY=e.values[1];gravityZ=e.values[2];sensorReady=true;return;}
        gravityX=a*gravityX+(1-a)*e.values[0];
        gravityY=a*gravityY+(1-a)*e.values[1];
        gravityZ=a*gravityZ+(1-a)*e.values[2];
        float x=e.values[0]-gravityX,y=e.values[1]-gravityY,z=e.values[2]-gravityZ;
        float strength=(float)Math.sqrt(x*x+y*y+z*z);
        long now=SystemClock.elapsedRealtime();
        if(strength>15.0f && now-lastShake>1500){
            lastShake=now;
            js("if(window.rtShake)window.rtShake();");
        }
    }
    @Override public void onAccuracyChanged(Sensor sensor,int accuracy) {}
    @Override public void onBackPressed() {
        if(webView==null){super.onBackPressed();return;}
        js("if(typeof go==='function' && !document.getElementById('home').classList.contains('active'))go('home');else if(typeof toast==='function')toast('再次按返回键可退出应用');");
        long now=SystemClock.elapsedRealtime();
        if(now-lastBack<1800)super.onBackPressed();
        lastBack=now;
    }
    private long lastBack=0;
    @Override protected void onDestroy() {
        worker.shutdownNow();
        if(sensorManager!=null)sensorManager.unregisterListener(this);
        if(webView!=null){webView.destroy();webView=null;}
        super.onDestroy();
    }
}
