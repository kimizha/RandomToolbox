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
import android.media.MediaMetadataRetriever;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.util.Base64;
import android.view.View;
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
    private static final String HOME_URL = "https://appassets.androidplatform.net/assets/index.html";
    private static final String[] MANIFEST_URLS = {
        "https://raw.githubusercontent.com/kimizha/RandomToolbox/dev/cloudbase-auth-integration/updates/version.json",
        "https://github.com/kimizha/RandomToolbox/raw/refs/heads/dev/cloudbase-auth-integration/updates/version.json"
    };
    private static final String[] HTML_URLS = {
        "https://raw.githubusercontent.com/kimizha/RandomToolbox/main/updates/index.html",
        "https://github.com/kimizha/RandomToolbox/raw/refs/heads/main/updates/index.html"
    };
    private static final int BUNDLED_WEB_VERSION = 12;
    private static final int MAX_HTML_BYTES = 2 * 1024 * 1024;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private WebView webView;
    private SharedPreferences prefs;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private Vibrator vibrator;
    private float gravityX, gravityY, gravityZ;
    private boolean sensorReady = false;
    private long lastShake = 0;
    private volatile boolean checking = false;
    private boolean restoring = false;
    private boolean pagePrepared = false;
    private String statusText = "自动检查更新 · 支持离线使用";
    private long lastBack = 0;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("rt_native_update", MODE_PRIVATE);
        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        accelerometer = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        applySystemTheme(false);
        webView = new WebView(this);
        webView.setBackgroundColor(0xfff6f7fb);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        webView.setVerticalScrollBarEnabled(false);
        webView.setHorizontalScrollBarEnabled(false);
        webView.setHapticFeedbackEnabled(true);
        webView.setOnLongClickListener(v -> true);
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        webView.setWebChromeClient(new WebChromeClient());
        webView.addJavascriptInterface(new NativeBridge(), "RandomToolboxNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                android.net.Uri uri = request.getUrl();
                if (!"https".equals(uri.getScheme()) || !"appassets.androidplatform.net".equals(uri.getHost())) return null;
                String path = uri.getPath();
                if (path == null || !path.startsWith("/assets/")) return null;
                String asset = path.substring(8);
                if (asset.isEmpty() || asset.startsWith("/") || asset.contains("..") || asset.indexOf(92) >= 0)
                    return new WebResourceResponse("text/plain", "UTF-8", new ByteArrayInputStream(new byte[0]));
                try {
                    String mime = android.webkit.MimeTypeMap.getSingleton().getMimeTypeFromExtension(android.webkit.MimeTypeMap.getFileExtensionFromUrl(asset));
                    if (asset.endsWith(".js")) mime = "application/javascript";
                    if (asset.endsWith(".html")) mime = "text/html";
                    if (mime == null) mime = "application/octet-stream";
                    return new WebResourceResponse(mime, "UTF-8", getAssets().open(asset));
                } catch (IOException e) {
                    return new WebResourceResponse("text/plain", "UTF-8", new ByteArrayInputStream(new byte[0]));
                }
            }
            @Override public void onPageFinished(WebView view, String url) {
                if (!HOME_URL.equals(url) || pagePrepared) return;
                pagePrepared = true;
                injectFeatures();
                if (restoring) {
                    restoring = false;
                    updateStatus("已恢复内置网页版本 " + BUNDLED_WEB_VERSION);
                    return;
                }
                // Keep bundled auth UI authoritative until signed multi-file web updates are supported.
                updateStatus("网页热更新暂未启用 · 可检查 APK 新版本");
                checkForUpdates(false);
            }
        });
        webView.loadUrl(HOME_URL);
    }
    private void applySystemTheme(boolean dark) {
        int color = dark ? 0xff10131d : 0xfff6f7fb;
        getWindow().setStatusBarColor(color);
        getWindow().setNavigationBarColor(color);
        int flags = getWindow().getDecorView().getSystemUiVisibility();
        flags = dark ? (flags & ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR & ~View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR)
                     : (flags | View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        getWindow().getDecorView().setSystemUiVisibility(flags);
        if (webView != null) webView.setBackgroundColor(color);
    }
    private void nativeVibrate(long[] pattern) {
        if (vibrator == null || !vibrator.hasVibrator()) return;
        try {
            if (Build.VERSION.SDK_INT >= 26) vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1));
            else vibrator.vibrate(pattern, -1);
        } catch (Exception ignored) {}
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
                file.delete(); updateHashFile().delete();
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
                try{var s=JSON.parse(localStorage.getItem('rt_settings')||'{}');RandomToolboxNative.setDarkMode(!!s.dark)}catch(e){}
                var settingsView=document.getElementById('settings');
                if(!settingsView)return;
                if(!document.getElementById('rtShakeRow')){
                  var vibe=document.getElementById('vibeToggle');
                  var row=document.createElement('div');row.className='setting';row.id='rtShakeRow';
                  var label=document.createElement('span');label.textContent='📱 摇一摇触发';
                  var box=document.createElement('input');box.type='checkbox';box.id='rtShakeToggle';
                  var state=JSON.parse(localStorage.getItem('rt_settings')||'{}');
                  box.checked=state.shake!==false;
                  box.onchange=function(){
                    var st=JSON.parse(localStorage.getItem('rt_settings')||'{}');
                    st.shake=box.checked;
                    localStorage.setItem('rt_settings',JSON.stringify(st));
                    if(typeof settings!=='undefined')settings.shake=box.checked;
                  };
                  row.appendChild(label);row.appendChild(box);
                  if(vibe&&vibe.closest('.setting'))vibe.closest('.setting').insertAdjacentElement('afterend',row);

                }
                if(!document.getElementById('rtUpdatePanel')){
                  var p=document.createElement('div');p.className='panel';p.id='rtUpdatePanel';
                  var title=document.createElement('h2');title.style.fontSize='17px';title.textContent='☁️ 版本更新';
                  var status=document.createElement('p');status.className='hint';status.id='rtUpdateStatus';
                  var diagnostic=document.createElement('pre');diagnostic.id='rtUpdateDiagnostic';diagnostic.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;line-height:1.6;color:var(--muted);margin:12px 0';
                  diagnostic.textContent='当前版本：V1.8 (code 7)\\n更新地址：dev 测试通道\\n等待检查…';
                  var check=document.createElement('button');check.className='secondary';
                  check.style.cssText='width:100%;margin-bottom:9px';check.textContent='检查 APK 更新';
                  check.onclick=function(){RandomToolboxNative.checkUpdate();};
                  var rollback=document.createElement('button');rollback.className='secondary';
                  rollback.style.width='100%';rollback.textContent='恢复内置版本';
                  rollback.onclick=function(){
                    if(typeof rtDialog==='function')rtDialog('恢复内置版本？','当前已下载的网页更新将被移除。',function(){RandomToolboxNative.rollback()});
                    else if(confirm('恢复内置版本？'))RandomToolboxNative.rollback();
                  };
                  p.appendChild(title);p.appendChild(status);p.appendChild(diagnostic);p.appendChild(check);p.appendChild(rollback);
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
        if (checking) { if (manual) updateStatus("正在检查，请稍候…"); return; }
        checking = true;
        if (manual) updateStatus("正在检查 APK 更新…");
        worker.execute(() -> {
            try {
                JSONObject manifest = new JSONObject(new String(downloadWithFallback(MANIFEST_URLS, 32768), StandardCharsets.UTF_8));
                int latestCode = manifest.optInt("apkVersionCode", 0);
                String link = manifest.optString("apkUrl", "");
                String notes = manifest.optString("apkNotes", "发现新版本");
                int current = getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
                String diag = "当前版本代码：" + current + "\\n服务器版本代码：" + latestCode + "\\n更新地址：" + MANIFEST_URLS[0] + "\\nAPK 地址：" + link;
                js("var e=document.getElementById('rtUpdateDiagnostic');if(e)e.textContent=" + JSONObject.quote(diag) + ";");
                if (latestCode > current && link.startsWith("https://github.com/kimizha/RandomToolbox/releases/")) {
                    main.post(() -> new android.app.AlertDialog.Builder(this)
                        .setTitle("发现随机工具箱新版本")
                        .setMessage(notes)
                        .setNegativeButton("稍后再说", null)
                        .setPositiveButton("前往下载", (dialog, which) -> {
                            android.content.Intent intent = new android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(link));
                            try { startActivity(intent); } catch (Exception e) { notifyUser("无法打开下载页面"); }
                        }).show());
                    updateStatus("发现 APK 新版本 " + latestCode);
                } else if (manual) {
                    updateStatus("当前没有可用的 APK 更新 · 网页热更新暂未启用");
                }
            } catch (Exception e) {
                if (manual) updateStatus("检查失败：" + e.getMessage());
                String diagError = "更新地址：" + MANIFEST_URLS[0] + "\\n检查异常：" + e.toString();
                js("var e=document.getElementById('rtUpdateDiagnostic');if(e)e.textContent=" + JSONObject.quote(diagError) + ";");
            } finally { checking = false; }
        });
    }
    private void legacyCheckForUpdates(boolean manual) {
        if (checking) { if (manual) updateStatus("正在检查更新，请稍候…"); return; }
        checking = true;
        if (manual) updateStatus("正在检查更新…");
        worker.execute(() -> {
            try {
                JSONObject manifest = new JSONObject(new String(downloadWithFallback(MANIFEST_URLS, 32768), StandardCharsets.UTF_8));
                int version = manifest.getInt("webVersion");
                String hash = manifest.getString("sha256").toLowerCase(Locale.ROOT);
                if (!hash.matches("[a-f0-9]{64}")) throw new IOException("更新配置中的 SHA-256 格式错误");
                int installed = Math.max(BUNDLED_WEB_VERSION, prefs.getInt("webVersion", BUNDLED_WEB_VERSION));
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
                byte[] bytes = downloadWithFallback(HTML_URLS, MAX_HTML_BYTES);
                if (!sha256(bytes).equals(hash)) throw new IOException("SHA-256 校验不一致，请检查更新文件");
                String html = new String(bytes, StandardCharsets.UTF_8);
                if (!validHtml(html)) throw new IOException("下载的 HTML 内容不符合要求");
                File tmp = new File(getFilesDir(), "randomtoolbox_update.tmp");
                File hashTmp = new File(getFilesDir(), "randomtoolbox_update.sha256.tmp");
                try (FileOutputStream out = new FileOutputStream(tmp)) { out.write(bytes); out.getFD().sync(); }
                try (FileOutputStream out = new FileOutputStream(hashTmp)) { out.write(hash.getBytes(StandardCharsets.US_ASCII)); out.getFD().sync(); }
                File dest = updateFile(), hashDest = updateHashFile();
                if (dest.exists() && !dest.delete()) throw new IOException("无法替换本地网页缓存");
                if (!tmp.renameTo(dest)) throw new IOException("无法保存本地网页缓存");
                if (hashDest.exists() && !hashDest.delete()) throw new IOException("无法替换校验文件");
                if (!hashTmp.renameTo(hashDest)) throw new IOException("无法保存校验文件");
                prefs.edit().putInt("webVersion", version).apply();
                updateStatus("已下载网页版本 " + version + "，正在应用…");
                applyHtml(html);
                main.postDelayed(() -> notifyUser("已更新到网页版本 " + version), 700);
            } catch (Exception e) {
                if (manual) updateStatus("更新失败：" + e.getMessage());
            } finally { checking = false; }
        });
    }
    private static byte[] downloadWithFallback(String[] addresses, int maxBytes) throws IOException {
        IOException last = null;
        StringBuilder errors = new StringBuilder();
        for (int i = 0; i < addresses.length; i++) {
            try { return download(addresses[i], maxBytes); }
            catch (IOException e) {
                last = e;
                if (errors.length() > 0) errors.append("；");
                errors.append("地址").append(i + 1).append("：").append(e.getMessage());
            }
        }
        throw new IOException("两个更新地址均失败（" + errors + "）", last);
    }
    private static byte[] download(String address, int maxBytes) throws IOException {
        HttpURLConnection conn = (HttpURLConnection) new URL(address).openConnection();
        conn.setConnectTimeout(9000); conn.setReadTimeout(12000);
        conn.setInstanceFollowRedirects(true);
        conn.setRequestProperty("Accept", "application/json, text/html, */*");
        conn.setRequestProperty("User-Agent", "RandomToolbox-Android/1.3.1");
        try {
            int code = conn.getResponseCode();
            if (code != 200) throw new IOException("HTTP " + code);
            return readLimited(conn.getInputStream(), maxBytes);
        } finally { conn.disconnect(); }
    }
    private static byte[] readLimited(InputStream input, int max) throws IOException {
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192]; int n, total = 0;
            while ((n = in.read(buf)) != -1) {
                total += n;
                if (total > max) throw new IOException("文件超过大小限制");
                out.write(buf, 0, n);
            }
            return out.toByteArray();
        }
    }
    private static String sha256(byte[] data) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder b = new StringBuilder();
        for (byte x : digest) b.append(String.format(Locale.ROOT, "%02x", x & 255));
        return b.toString();
    }
    public class NativeBridge {
        @JavascriptInterface public void vibrate(int milliseconds) {
            int ms = Math.max(1, Math.min(500, milliseconds));
            nativeVibrate(new long[]{0, ms});
        }
        @JavascriptInterface public void vibratePattern(String patternJson) {
            try {
                org.json.JSONArray arr = new org.json.JSONArray(patternJson);
                int count = Math.min(arr.length(), 12);
                if (count == 0) return;
                long[] pattern = new long[count + 1];
                pattern[0] = 0;
                for (int i = 0; i < count; i++) pattern[i + 1] = Math.max(0, Math.min(500, arr.getLong(i)));
                nativeVibrate(pattern);
            } catch (Exception ignored) {}
        }
        @JavascriptInterface public void setDarkMode(boolean dark) { main.post(() -> applySystemTheme(dark)); }
        @JavascriptInterface public String getMusicCover(String relativePath) {
            if (relativePath == null || !relativePath.startsWith("music/")
                || !relativePath.toLowerCase(Locale.ROOT).endsWith(".mp3")
                || relativePath.contains("..") || relativePath.contains("\\")
                || relativePath.startsWith("/")) return "";
            MediaMetadataRetriever retriever = new MediaMetadataRetriever();
            File temp = null;
            try {
                temp = File.createTempFile("rt_cover_", ".mp3", getCacheDir());
                try (InputStream in = getAssets().open(relativePath);
                     FileOutputStream out = new FileOutputStream(temp)) {
                    byte[] buffer = new byte[32768]; int n;
                    while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
                }
                retriever.setDataSource(temp.getAbsolutePath());
                byte[] picture = retriever.getEmbeddedPicture();
                if (picture == null || picture.length == 0 || picture.length > 2 * 1024 * 1024) return "";
                String mime = "image/jpeg";
                if (picture.length > 3 && (picture[0] & 255) == 0x89 && (picture[1] & 255) == 0x50) mime = "image/png";
                else if (picture.length > 3 && (picture[0] & 255) == 0x52 && (picture[1] & 255) == 0x49) mime = "image/webp";
                return "data:" + mime + ";base64," + Base64.encodeToString(picture, Base64.NO_WRAP);
            } catch (Exception e) {
                android.util.Log.w("RandomToolbox", "读取音乐封面失败: " + relativePath, e);
                return "";
            } finally {
                try { retriever.release(); } catch (Exception ignored) {}
                if (temp != null) temp.delete();
            }
        }
        @JavascriptInterface public void checkUpdate() { main.post(() -> checkForUpdates(true)); }
        @JavascriptInterface public void rollback() {
            main.post(() -> worker.execute(() -> {
                int v = prefs.getInt("webVersion", BUNDLED_WEB_VERSION);
                prefs.edit().putInt("blockedVersion", v).remove("webVersion").commit();
                updateFile().delete(); updateHashFile().delete();
                main.post(() -> { restoring = true; pagePrepared = false; webView.loadUrl(HOME_URL); });
            }));
        }
    }
    @Override protected void onResume() {
        super.onResume(); sensorReady = false;
        if (sensorManager != null && accelerometer != null)
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_GAME);
        if (webView != null) webView.onResume();
    }
    @Override protected void onPause() {
        if (sensorManager != null) sensorManager.unregisterListener(this);
        if (webView != null) webView.onPause();
        super.onPause();
    }
    @Override public void onSensorChanged(SensorEvent e) {
        if (e.sensor.getType() != Sensor.TYPE_ACCELEROMETER || webView == null) return;
        float a = .82f;
        if (!sensorReady) {
            gravityX = e.values[0]; gravityY = e.values[1]; gravityZ = e.values[2];
            sensorReady = true; return;
        }
        gravityX = a * gravityX + (1 - a) * e.values[0];
        gravityY = a * gravityY + (1 - a) * e.values[1];
        gravityZ = a * gravityZ + (1 - a) * e.values[2];
        float x = e.values[0] - gravityX, y = e.values[1] - gravityY, z = e.values[2] - gravityZ;
        float strength = (float) Math.sqrt(x * x + y * y + z * z);
        long now = SystemClock.elapsedRealtime();
        if (strength > 15.0f && now - lastShake > 1500) {
            lastShake = now; js("if(window.rtShake)window.rtShake();");
        }
    }
    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) {}
    @Override public void onBackPressed() {
        if (webView == null) { super.onBackPressed(); return; }
        webView.evaluateJavascript("(function(){if(document.getElementById('rtModalShade')){document.getElementById('rtModalShade').remove();return 'handled'}var a=document.querySelector('.view.active');if(a&&a.id!=='home'){if(a.id==='game')go('games');else if(a.id==='tool'||a.id==='manage')go('home');else if(a.id==='ideas')go('catalog');else go('home');return 'handled'}return 'home'})()", result -> {
            if ("\"handled\"".equals(result)) { lastBack = 0; return; }
            long now = SystemClock.elapsedRealtime();
            if (now - lastBack < 1800) MainActivity.super.onBackPressed();
            else notifyUser("再次按返回键可退出应用");
            lastBack = now;
        });
    }
    @Override protected void onDestroy() {
        worker.shutdownNow();
        if (sensorManager != null) sensorManager.unregisterListener(this);
        if (webView != null) { webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
