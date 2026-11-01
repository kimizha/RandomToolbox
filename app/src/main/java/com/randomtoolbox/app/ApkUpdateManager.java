package com.randomtoolbox.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import org.json.JSONObject;

/** Replaces the former APK dialog. Enforcement is native and never depends on a web resource version. */
public final class ApkUpdateManager {
    public static final String CONFIG_URL="https://raw.githubusercontent.com/kimizha/RandomToolbox/ui/android-happybox-redesign/updates/version.json";
    private static final long DEADLINE_MS=12000L;
    interface Fetcher { String fetch() throws Exception; }
    private Fetcher fetcher;
    public interface Host { void status(String message,boolean failed); void feedback(); }
    private final Activity activity;
    private final FrameLayout root;
    private final WebView web;
    private final SharedPreferences prefs;
    private final ExecutorService executor;
    private final Host host;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ApkUpdatePolicy.Session state=new ApkUpdatePolicy.Session();
    private final long installedCode;
    private final String installedName;
    private final ConnectivityManager connectivity;
    private ConnectivityManager.NetworkCallback networkCallback;
    private volatile HttpURLConnection connection;
    private Future<?> request;
    private View overlay;
    private String screen="", status="尚未检查 APK 更新";
    private boolean destroyed, started, foreground, returnedFromBrowser, wasOffline, dark, vibe=true;
    private boolean pendingManual, offlineNoticeShown;
    private long lastOffered=-1;
    private int animationMs=220, offlineFailures;
    private final Runnable periodic=()->check(false,false);
    private final Runnable offlineRetry=()->check(false,true);
    private Runnable timeout;

    public ApkUpdateManager(Activity activity,FrameLayout root,WebView web,SharedPreferences prefs,ExecutorService executor,Host host) throws Exception {
        this.activity=activity;this.root=root;this.web=web;this.prefs=prefs;this.executor=executor;this.host=host;
        PackageInfo info=activity.getPackageManager().getPackageInfo(activity.getPackageName(),0);
        installedCode=Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode;
        installedName=info.versionName==null?String.valueOf(installedCode):info.versionName;
        connectivity=(ConnectivityManager)activity.getSystemService(Context.CONNECTIVITY_SERVICE);
        fetcher=this::fetch;
    }
    // Package-private transport seam for offline native UI tests, never exposed to the WebView bridge.
    ApkUpdateManager(Activity a,FrameLayout r,WebView w,SharedPreferences p,ExecutorService e,Host h,Fetcher f) throws Exception {
        this(a,r,w,p,e,h);fetcher=f;
    }
    public void start() {
        if(started)return;started=true;wasOffline=!hasNetwork();
        // Cache is informational only: it must never lock the user before a fresh successful check.
        String cached=prefs.getString("apk_config_cache_v1","");
        if(!cached.isEmpty())try{ApkUpdatePolicy.Config c=ApkUpdatePolicy.parse(cached);publish("上次获取到版本 "+c.latestName+"，正在核对最新配置…",false);}catch(Exception ignored){}
        if(connectivity!=null){networkCallback=new ConnectivityManager.NetworkCallback(){
            @Override public void onAvailable(Network n){main.post(()->{if(destroyed)return;if(wasOffline){wasOffline=false;check(false,true);}});}
            @Override public void onLost(Network n){main.post(()->{if(destroyed||hasNetwork())return;wasOffline=true;boolean blocking=state.blocking;cancelTransport();state.networkLost();unblock();publish("网络已断开，可以继续使用本地功能；联网后会重试",true);if(blocking)showOffline();scheduleOfflineRetry();});}
        };try{connectivity.registerDefaultNetworkCallback(networkCallback);}catch(Exception ignored){networkCallback=null;}}
        check(false,true);
    }
    public boolean isBlocking(){return state.blocking;}
    public void onPageReady(){publish(status,state.offline);}
    public void onResume(){foreground=true;if(!started)return;if(returnedFromBrowser||state.blocking||state.offline||state.due(System.currentTimeMillis())){returnedFromBrowser=false;check(false,true);}else schedule();}
    public void onPause(){foreground=false;main.removeCallbacks(periodic);main.removeCallbacks(offlineRetry);}
    public void preferences(String json){try{JSONObject s=new JSONObject(json);dark=s.optBoolean("dark",dark);vibe=s.optBoolean("vibe",true);String speed=s.optString("speed","normal");animationMs="fast".equals(speed)?140:"slow".equals(speed)?340:220;redraw();}catch(Exception ignored){}}
    public void darkMode(boolean value){if(dark!=value){dark=value;redraw();}}
    public void manual(){check(true,true);}
    private boolean hasNetwork(){try{return connectivity!=null&&connectivity.getActiveNetwork()!=null;}catch(Exception e){return true;}}
    private void check(boolean manual,boolean urgent){
        if(destroyed)return;
        if(state.checking){pendingManual|=manual;publish("正在检查 APK 更新，请稍候…",false);return;}
        if(!urgent&&!state.due(System.currentTimeMillis())){schedule();return;}
        long token=state.begin();if(token==0)return;
        main.removeCallbacks(offlineRetry);pendingManual=manual;publish("正在检查 APK 更新…",false);redraw();
        timeout=()->{if(state.failure(token)){cancelTransport();unblock();publish("检查超时，可以继续使用本地功能",true);if(pendingManual||!offlineNoticeShown)showOffline();scheduleOfflineRetry();}};
        main.postDelayed(timeout,DEADLINE_MS);
        request=executor.submit(()->{
            try{
                String raw=fetcher.fetch();ApkUpdatePolicy.Config config=ApkUpdatePolicy.parse(raw);
                // Validate the decision before writing a cache or presenting any mandatory UI.
                config.decide(installedCode);
                main.post(()->{if(destroyed)return;try{
                    if(!state.success(token,config,installedCode,System.currentTimeMillis()))return;
                    finishTimeout();offlineNoticeShown=false;offlineFailures=0;prefs.edit().putString("apk_config_cache_v1",raw).putLong("apk_config_cached_at",System.currentTimeMillis()).apply();
                    ApkUpdatePolicy.Decision decision=config.decide(installedCode);
                    if(decision==ApkUpdatePolicy.Decision.FORCED){publish("需要更新 APK 后继续使用",false);showUpdate(true);}
                    else{unblock();if("forced".equals(screen)||"offline".equals(screen))hide();
                        if(decision==ApkUpdatePolicy.Decision.OPTIONAL){publish("发现新版本 "+config.latestName,false);if(pendingManual||lastOffered!=config.latestCode){lastOffered=config.latestCode;showUpdate(false);}}
                        else{if("optional".equals(screen))hide();publish("当前 APK "+installedName+"（"+installedCode+"），已是最新版本",false);}
                    }pendingManual=false;schedule();
                }catch(Exception e){fail(token);}});
            }catch(Exception e){main.post(()->fail(token));}
        });
    }
    private void fail(long token){boolean blocked=state.blocking;if(destroyed||!state.failure(token))return;finishTimeout();unblock();publish("暂时无法获取有效更新配置，可以继续使用本地功能",true);if(blocked||pendingManual||!offlineNoticeShown)showOffline();else if("forced".equals(screen))hide();scheduleOfflineRetry();}
    private void finishTimeout(){if(timeout!=null)main.removeCallbacks(timeout);timeout=null;request=null;}
    private void cancelTransport(){if(timeout!=null)main.removeCallbacks(timeout);timeout=null;Future<?> f=request;request=null;if(f!=null)f.cancel(true);HttpURLConnection c=connection;connection=null;if(c!=null)try{executor.execute(c::disconnect);}catch(RuntimeException ignored){}}
    private void schedule(){main.removeCallbacks(periodic);if(foreground&&!destroyed&&state.config!=null&&!state.offline)main.postDelayed(periodic,state.config.intervalMillis);}
    private void scheduleOfflineRetry(){main.removeCallbacks(offlineRetry);if(foreground&&!destroyed){main.postDelayed(offlineRetry,ApkUpdatePolicy.retryDelay(offlineFailures));offlineFailures=Math.min(4,offlineFailures+1);}}
    private void publish(String text,boolean failed){status=text;host.status(text,failed);}
    private String fetch() throws Exception {
        String url=CONFIG_URL+"?rt_ts="+System.currentTimeMillis();
        // No alternate branch fallback: it could accidentally reapply a revoked policy.
        for(int redirects=0;redirects<3;redirects++){
            URL target=new URL(url);if(!"https".equalsIgnoreCase(target.getProtocol()))throw new IllegalArgumentException("HTTPS required");
            HttpURLConnection c=(HttpURLConnection)target.openConnection();connection=c;
            c.setConnectTimeout(4000);c.setReadTimeout(4000);c.setUseCaches(false);c.setInstanceFollowRedirects(false);
            c.setRequestProperty("Cache-Control","no-cache, no-store, max-age=0");c.setRequestProperty("Pragma","no-cache");c.setRequestProperty("Accept","application/json");c.setRequestProperty("User-Agent","HappyBox-Android/"+installedName);
            try{
                int code=c.getResponseCode();if(code>=300&&code<400){String next=c.getHeaderField("Location");if(next==null)throw new IllegalArgumentException("Redirect missing");URL u=new URL(target,next);String host=u.getHost();if(!"https".equalsIgnoreCase(u.getProtocol())||!("raw.githubusercontent.com".equalsIgnoreCase(host)||"github.com".equalsIgnoreCase(host)))throw new IllegalArgumentException("Unexpected redirect");url=u.toString();continue;}
                if(code!=200)throw new IllegalArgumentException("HTTP status");
                try(InputStream input=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
                    byte[] buf=new byte[4096];int n;while((n=input.read(buf))!=-1){if(Thread.currentThread().isInterrupted())throw new InterruptedException();if(out.size()+n>32768)throw new IllegalArgumentException("Configuration too large");out.write(buf,0,n);}return new String(out.toByteArray(),StandardCharsets.UTF_8);
                }
            }finally{c.disconnect();if(connection==c)connection=null;}
        }throw new IllegalArgumentException("Redirect limit");
    }
    private void showUpdate(boolean forced){screen=forced?"forced":"optional";render();}
    private void showOffline(){offlineNoticeShown=true;screen="offline";render();}
    private void redraw(){if(!screen.isEmpty()&&overlay!=null)render();}
    private void unblock(){web.setVisibility(View.VISIBLE);web.setEnabled(true);web.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_AUTO);}
    private void hide(){if(overlay!=null){root.removeView(overlay);overlay=null;}screen="";if(!state.blocking)unblock();}
    public boolean back(){if(state.blocking)return true;if(overlay!=null){hide();return true;}return false;}
    private void download(){
        if(returnedFromBrowser)return;
        ApkUpdatePolicy.Config c=state.config;
        if(c==null||!ApkUpdatePolicy.validDownloadUrl(c.downloadUrl)){publish("下载地址暂不可用，请重试检查更新",true);return;}
        try{
            Intent intent=new Intent(Intent.ACTION_VIEW,Uri.parse(c.downloadUrl));intent.addCategory(Intent.CATEGORY_BROWSABLE);
            PackageManager pm=activity.getPackageManager();Intent browser=Intent.makeMainSelectorActivity(Intent.ACTION_MAIN,Intent.CATEGORY_APP_BROWSER);
            List<ResolveInfo> browsers=pm.queryIntentActivities(browser,0);
            ResolveInfo preferred=pm.resolveActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://www.example.com")),PackageManager.MATCH_DEFAULT_ONLY);
            String browserPackage=null;for(ResolveInfo r:browsers)if(r.activityInfo!=null){if(browserPackage==null)browserPackage=r.activityInfo.packageName;if(preferred!=null&&preferred.activityInfo!=null&&r.activityInfo.packageName.equals(preferred.activityInfo.packageName)){browserPackage=r.activityInfo.packageName;break;}}
            if(browserPackage==null)throw new android.content.ActivityNotFoundException();intent.setPackage(browserPackage);
            returnedFromBrowser=true;activity.startActivity(intent);
        }catch(Exception e){returnedFromBrowser=false;publish("无法打开浏览器，请安装或启用系统浏览器后重试",true);if(overlay!=null)render();}
    }
    private int dp(float n){return Math.round(n*activity.getResources().getDisplayMetrics().density);}
    private GradientDrawable shape(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}
    private TextView text(String value,int size,int color,boolean bold){TextView t=new TextView(activity);t.setText(value);t.setTextSize(size);t.setTextColor(color);if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);t.setLineSpacing(dp(4),1);return t;}
    private void add(LinearLayout parent,View child,int margin){LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(margin);parent.addView(child,lp);}
    private Button button(String label,boolean primary,Runnable action){Button b=new Button(activity);b.setText(label);b.setTextSize(16);b.setAllCaps(false);b.setTextColor(primary?Color.WHITE:(dark?0xffcab3ff:0xff7955be));b.setBackground(shape(primary?0xff9274d4:(dark?0xff30283e:0xffefe7fb),16));b.setMinHeight(dp(52));b.setPadding(dp(12),dp(12),dp(12),dp(12));b.setOnClickListener(v->{if(vibe)host.feedback();action.run();});return b;}
    private void render(){
        if(destroyed||screen.isEmpty())return;
        if(overlay!=null)root.removeView(overlay);
        boolean forced="forced".equals(screen),offline="offline".equals(screen);
        int bg=dark?0xff19181f:0xfff8f7fc,card=dark?0xff25212e:Color.WHITE,ink=dark?0xfff4effa:0xff2d2739,muted=dark?0xffb2a9bf:0xff8c8398;
        FrameLayout shade=new FrameLayout(activity);shade.setBackgroundColor(forced?bg:0x991b1528);shade.setClickable(true);shade.setFocusable(true);shade.setFocusableInTouchMode(true);shade.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        ScrollView scroll=new ScrollView(activity);scroll.setFillViewport(false);scroll.setClipToPadding(false);
        LinearLayout content=new LinearLayout(activity);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(24),dp(26),dp(24),dp(24));content.setBackground(shape(forced?bg:card,26));scroll.addView(content);
        TextView icon=text("↑",36,dark?0xffd5bfff:0xff8460c4,true);icon.setGravity(Gravity.CENTER);icon.setBackground(shape(dark?0xff392e49:0xffeee5fb,22));LinearLayout.LayoutParams iconLp=new LinearLayout.LayoutParams(dp(68),dp(68));content.addView(icon,iconLp);
        ApkUpdatePolicy.Config c=state.config;
        add(content,text(offline?"暂时无法检查更新":c!=null?c.title:forced?"开心盒重要更新":"开心盒有新版本",24,ink,true),24);
        add(content,text("当前版本 "+installedName+"（"+installedCode+"）"+(!offline&&c!=null?"\n最新版本 "+c.latestName+"（"+c.latestCode+"）":""),13,muted,false),14);
        add(content,text(offline?"未能取得最新有效配置，暂不限制本地功能。若上次曾要求更新，也以联网后重新核对的结果为准。":c==null?"":c.message,16,ink,false),20);
        if(!offline)add(content,text("将在系统浏览器打开蓝奏云页面，请自行下载 APK 并确认安装。",12,muted,false),16);
        add(content,text(status,12,muted,false),14);
        if(offline){add(content,button(state.checking?"正在重试…":"重试",true,()->check(true,true)),22);add(content,button("继续使用本地功能",false,this::hide),10);}
        else{add(content,button("立即更新",true,this::download),22);if(forced)add(content,button(state.checking?"正在重新检查…":"重新检查更新状态",false,()->check(true,true)),10);else add(content,button("稍后再说",false,this::hide),10);}
        for(int i=0;i<content.getChildCount();i++){View v=content.getChildAt(i);if(v instanceof Button&&((Button)v).getText().toString().contains("正在"))v.setEnabled(false);}
        FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(-1,-2,Gravity.CENTER);lp.leftMargin=dp(forced?12:20);lp.rightMargin=lp.leftMargin;lp.topMargin=dp(20);lp.bottomMargin=dp(20);shade.addView(scroll,lp);
        root.addView(shade,new FrameLayout.LayoutParams(-1,-1));overlay=shade;
        if(forced){web.evaluateJavascript("if(window.hbPartyPause)window.hbPartyPause();if(typeof gameTimerStop==='function')gameTimerStop();",null);web.clearFocus();android.view.inputmethod.InputMethodManager ime=(android.view.inputmethod.InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);if(ime!=null)ime.hideSoftInputFromWindow(web.getWindowToken(),0);web.setVisibility(View.INVISIBLE);web.setEnabled(false);web.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);}
        else unblock();
        if(!forced)shade.setOnClickListener(v->hide());scroll.setOnClickListener(v->{});
        shade.requestFocus();if(animationMs>0){content.setAlpha(.6f);content.animate().alpha(1).setDuration(animationMs).start();}
    }
    public void destroy(){destroyed=true;main.removeCallbacksAndMessages(null);cancelTransport();if(networkCallback!=null&&connectivity!=null)try{connectivity.unregisterNetworkCallback(networkCallback);}catch(Exception ignored){}hide();}
}
