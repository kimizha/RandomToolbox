package com.randomtoolbox.app;

import android.app.Activity;
import android.os.Bundle;
import android.content.Context;
import android.content.SharedPreferences;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.graphics.Color;
import android.util.Base64;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity implements SensorEventListener {
    // 修改 GitHub 仓库默认分支时，也要修改此地址。
    private static final String MANIFEST_URL =
        "https://raw.githubusercontent.com/kimizha/RandomToolbox/main/updates/version.json";
    private static final String HTML_URL =
        "https://raw.githubusercontent.com/kimizha/RandomToolbox/main/updates/index.html";
    private static final int BUNDLED_WEB_VERSION = 12;
    private static final int MAX_HTML_BYTES = 2 * 1024 * 1024;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private WebView webView;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private SharedPreferences prefs;
    private boolean checking = false;
    private long lastShake = 0;
    private float gravityX, gravityY, gravityZ;
    private boolean sensorReady = false;

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
                if (!url.startsWith("file:///android_asset/index.html")) return;
                injectFeatures();
                loadSavedWebUpdate();
                checkForUpdates(false);
            }
        });
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void js(String script) {
        main.post(() -> { if (webView != null) webView.evaluateJavascript(script, null); });
    }
    private void notifyUser(String message) {
        js("if(typeof toast==='function')toast(" + JSONObject.quote(message) + ");");
    }
    private File updateFile() { return new File(getFilesDir(), "randomtoolbox_update.html"); }

    private void loadSavedWebUpdate() {
        File file = updateFile();
        if (!file.isFile()) return;
        worker.execute(() -> {
            try {
                byte[] bytes = readLimited(new FileInputStream(file), MAX_HTML_BYTES);
                String html = new String(bytes, StandardCharsets.UTF_8);
                if (!validHtml(html)) throw new IOException("invalid saved html");
                applyHtml(html);
            } catch (Exception e) {
                file.delete();
                prefs.edit().remove("webVersion").apply();
                notifyUser("云端缓存已损坏，已恢复内置版本");
            }
        });
    }

    private boolean validHtml(String html) {
        return html.length() > 1000 && html.contains("<html") &&
               html.contains("</html>") && html.contains("随机工具箱") &&
               html.contains("function openTool(") && html.contains("function go(");
    }
    private void applyHtml(String html) {
        // 保持 file:///android_asset/ 页面上下文，不更换 localStorage 的来源。
        // 先加载内置页，再 document.write 更新内容；不向 WebView 开放任意网址。
        String base64 = Base64.encodeToString(html.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
        js("(function(){try{var bytes=Uint8Array.from(atob('" + base64 + "'),c=>c.charCodeAt(0));" +
           "var html=new TextDecoder('utf-8').decode(bytes);document.open();document.write(html);document.close();" +
           "setTimeout(function(){" + featureScript() + "},180);" +
           "}catch(e){console.error('更新加载失败',e);}})();");
    }

    private void injectFeatures() { js(featureScript()); }
    private String featureScript() {
        return "(function(){" +
            "if(!window.__rtShakeInstalled){window.__rtShakeInstalled=true;" +
            "window.rtShake=function(){try{var s=JSON.parse(localStorage.getItem('rt_settings')||'{}');" +
            "if(s.shake===false||typeof busy==='undefined'||busy||" +
            "!document.getElementById('tool').classList.contains('active'))return;" +
            "var f={coin:'flipCoin',number:'genNumber',wheel:'spinWheel',dice:'rollDice',rps:'playRps',draw:'drawOne'}[activeTool];" +
            "if(f&&typeof window[f]==='function')window[f]();}catch(e){}};}" +
            "var settingsView=document.getElementById('settings');if(!settingsView)return;" +
            "if(!document.getElementById('rtShakeRow')){" +
            "var panel=settingsView.querySelector('.panel');if(panel){" +
            "var row=document.createElement('div');row.className='setting';row.id='rtShakeRow';" +
            "var label=document.createElement('span');label.textContent='📳 摇一摇触发';" +
            "var box=document.createElement('input');box.type='checkbox';box.id='rtShakeToggle';" +
            "var state=JSON.parse(localStorage.getItem('rt_settings')||'{}');box.checked=state.shake!==false;" +
            "box.onchange=function(){var st=JSON.parse(localStorage.getItem('rt_settings')||'{}');" +
            "st.shake=box.checked;localStorage.setItem('rt_settings',JSON.stringify(st));" +
            "if(typeof settings!=='undefined')settings.shake=box.checked;};" +
            "row.appendChild(label);row.appendChild(box);panel.appendChild(row);}}" +
            "if(!document.getElementById('rtUpdatePanel')){" +
            "var p=document.createElement('div');p.className='panel';p.id='rtUpdatePanel';" +
            "p.innerHTML='<h2 style=\"font-size:17px\">☁️ 云端更新</h2>' +" +
            "'<p class=\"hint\" id=\"rtUpdateStatus\">自动检查更新 · 支持离线使用</p>' +" +
            "'<button class=\"secondary\" style=\"width:100%;margin-bottom:9px\" onclick=\"RandomToolboxNative.checkUpdate()\">检查更新</button>' +" +
            "'<button class=\"secondary\" style=\"width:100%\" onclick=\"if(confirm(\\\"恢复内置版本？将暂停当前云端版本的自动更新。\\\"))RandomToolboxNative.rollback()\">恢复内置版本</button>';" +
            "settingsView.appendChild(p);}" +
            "})();";
    }
    private void updateStatus(String text) {
        js("var e=document.getElementById('rtUpdateStatus');if(e)e.textContent=" + JSONObject.quote(text) + ";");
    }

    private void checkForUpdates(boolean manual) {
        if (checking) return;
        checking = true;
        if (manual) updateStatus("正在检查更新…");
        worker.execute(() -> {
            try {
                JSONObject manifest = new JSONObject(new String(download(MANIFEST_URL, 32768), StandardCharsets.UTF_8));
                int version = manifest.getInt("webVersion");
                String hash = manifest.getString("sha256").toLowerCase(java.util.Locale.ROOT);
                if (!hash.matches("[a-f0-9]{64}")) throw new IOException("sha256 invalid");
                int installed = prefs.getInt("webVersion", BUNDLED_WEB_VERSION);
                int blocked = prefs.getInt("blockedVersion", -1);
                if (version <= installed || version == blocked) {
                    if (manual) updateStatus("当前已是最新版本（网页版本 " + installed + "）");
                    return;
                }
                // URL 固定，服务器清单不能指定任意下载地址。
                updateStatus("发现新版，正在安全下载…");
                byte[] htmlBytes = download(HTML_URL, MAX_HTML_BYTES);
                if (!sha256(htmlBytes).equals(hash)) throw new IOException("SHA-256 mismatch");
                String html = new String(htmlBytes, StandardCharsets.UTF_8);
                if (!validHtml(html)) throw new IOException("HTML validation failed");
                File tmp = new File(getFilesDir(), "randomtoolbox_update.tmp");
                try (FileOutputStream out = new FileOutputStream(tmp)) {
                    out.write(htmlBytes);out.getFD().sync();
                }
                File dest = updateFile();
                if (dest.exists() && !dest.delete()) throw new IOException("cannot replace old update");
                if (!tmp.renameTo(dest)) throw new IOException("cannot commit update");
                prefs.edit().putInt("webVersion", version).apply();
                main.post(() -> {
                    updateStatus("已下载网页版本 " + version + "，正在应用…");
                    applyHtml(html);
                    main.postDelayed(() -> notifyUser("已更新到云端网页版本 " + version), 550);
                });
            } catch (Exception e) {
                if (manual) updateStatus("检查失败，请检查网络或云端版本文件");
            } finally { checking = false; }
        });
    }

    private static byte[] download(String address, int maxBytes) throws IOException {
        HttpURLConnection conn = (HttpURLConnection) new URL(address).openConnection();
        conn.setConnectTimeout(9000);conn.setReadTimeout(12000);
        conn.setInstanceFollowRedirects(true);
        try {
            if (conn.getResponseCode() != 200) throw new IOException("HTTP " + conn.getResponseCode());
            return readLimited(conn.getInputStream(), maxBytes);
        } finally { conn.disconnect(); }
    }
    private static byte[] readLimited(InputStream input, int max) throws IOException {
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192];int n,total=0;
            while ((n=in.read(buf))!=-1) {total+=n;if(total>max)throw new IOException("file too large");out.write(buf,0,n);}
            return out.toByteArray();
        }
    }
    private static String sha256(byte[] data) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder b=new StringBuilder();for(byte x:digest)b.append(String.format("%02x",x&255));return b.toString();
    }

    public class NativeBridge {
        @JavascriptInterface public void checkUpdate() { main.post(() -> checkForUpdates(true)); }
        @JavascriptInterface public void rollback() {
            main.post(() -> {
                int v=prefs.getInt("webVersion",BUNDLED_WEB_VERSION);
                prefs.edit().putInt("blockedVersion",v).remove("webVersion").apply();
                updateFile().delete();
                webView.loadUrl("file:///android_asset/index.html");
            });
        }
    }
    @Override protected void onResume() {
        super.onResume();sensorReady=false;
        if (sensorManager!=null && accelerometer!=null)
            sensorManager.registerListener(this,accelerometer,SensorManager.SENSOR_DELAY_GAME);
        if (webView!=null)webView.onResume();
    }
    @Override protected void onPause() {
        if(sensorManager!=null)sensorManager.unregisterListener(this);
        if(webView!=null)webView.onPause();super.onPause();
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
        long now=android.os.SystemClock.elapsedRealtime();
        if(strength>15.0f && now-lastShake>1500){lastShake=now;js("if(window.rtShake)window.rtShake();");}
    }
    @Override public void onAccuracyChanged(Sensor sensor,int accuracy) {}
    @Override public void onBackPressed() {
        if(webView!=null){
            js("if(document.getElementById('tool').classList.contains('active')||document.getElementById('manage').classList.contains('active'))go('home');else if(!document.getElementById('home').classList.contains('active'))go('home');else window.RandomToolboxNative&&void(0);");
        }else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        worker.shutdownNow();if(sensorManager!=null)sensorManager.unregisterListener(this);
        if(webView!=null){webView.destroy();webView=null;}super.onDestroy();
    }
}
