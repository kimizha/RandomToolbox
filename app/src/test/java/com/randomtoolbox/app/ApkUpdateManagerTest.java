package com.randomtoolbox.app;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.ResolveInfo;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.FrameLayout;
import org.json.JSONObject;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.Shadows;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.LooperMode;
import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.AbstractExecutorService;
import java.util.concurrent.TimeUnit;
import static org.junit.Assert.*;

/** Android native views/lifecycle with an offline injected transport, not a live update server. */
@RunWith(RobolectricTestRunner.class)
@Config(sdk=28)
@LooperMode(LooperMode.Mode.PAUSED)
public class ApkUpdateManagerTest {
    Activity activity;FrameLayout root;WebView web;ApkUpdateManager manager;
    String response,status;boolean throwTransport;int requests,feedback;
    long installed;
    static class TestExecutor extends AbstractExecutorService {
        boolean stopped,hold;
        public void execute(Runnable r){if(!hold)r.run();}
        public void shutdown(){stopped=true;}
        public List<Runnable> shutdownNow(){stopped=true;return Collections.emptyList();}
        public boolean isShutdown(){return stopped;}
        public boolean isTerminated(){return stopped;}
        public boolean awaitTermination(long n,TimeUnit u){return true;}
    }
    TestExecutor executor;
    @Before public void setup() throws Exception {
        activity=Robolectric.buildActivity(Activity.class).setup().get();root=new FrameLayout(activity);web=new WebView(activity);root.addView(web);activity.setContentView(root);
        installed=activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).getLongVersionCode();
        response=json(installed+10,installed+1,false).toString();executor=new TestExecutor();
        manager=new ApkUpdateManager(activity,root,web,activity.getSharedPreferences("apk-update-native-test",0),executor,new ApkUpdateManager.Host(){public void status(String s,boolean failed){status=s;}public void feedback(){feedback++;}},()->{requests++;if(throwTransport)throw new IOException("offline fixture");return response;});
        manager.onResume();
    }
    JSONObject json(long latest,long min,boolean force)throws Exception{return new JSONObject().put("latestVersionCode",latest).put("latestVersionName","3.0").put("minSupportedVersionCode",Math.max(1,min)).put("forceUpdate",force).put("downloadUrl","https://test-fixture.lanzou.com/parser-only").put("updateTitle","开心盒更新测试").put("updateMessage","这是离线原生界面测试，不访问远程服务。").put("checkIntervalHours",6);}
    void idle(){Shadows.shadowOf(Looper.getMainLooper()).idle();}
    void start(){manager.start();idle();}
    Button button(View view,String label){if(view instanceof Button&&((Button)view).getText().toString().equals(label))return (Button)view;if(view instanceof ViewGroup){ViewGroup g=(ViewGroup)view;for(int i=0;i<g.getChildCount();i++){Button result=button(g.getChildAt(i),label);if(result!=null)return result;}}return null;}
    void force()throws Exception{response=json(installed+10,installed+1,true).toString();start();}
    @After public void cleanup(){manager.destroy();web.destroy();activity.finish();}
    @Test public void newestHasNoOverlay()throws Exception{response=json(installed,Math.max(1,installed),false).toString();start();assertFalse(manager.isBlocking());assertEquals(1,root.getChildCount());assertEquals(View.VISIBLE,web.getVisibility());}
    @Test public void ordinaryCanBeDeferred(){start();assertFalse(manager.isBlocking());assertNotNull(button(root,"立即更新"));assertNotNull(button(root,"稍后再说"));button(root,"稍后再说").performClick();assertEquals(1,root.getChildCount());assertEquals(View.VISIBLE,web.getVisibility());}
    @Test public void forcedCannotBeDismissedOrReachedThroughWebView()throws Exception{force();assertTrue(manager.isBlocking());assertEquals(View.INVISIBLE,web.getVisibility());assertFalse(web.isEnabled());assertNull(button(root,"稍后再说"));assertTrue(manager.back());assertTrue(manager.back());root.getChildAt(1).performClick();assertTrue(manager.isBlocking());assertEquals(2,root.getChildCount());}
    @Test public void remoteEmergencyOffRestoresOrdinaryView()throws Exception{force();response=json(installed+10,installed+1,false).toString();manager.onPause();manager.onResume();idle();assertFalse(manager.isBlocking());assertEquals(View.VISIBLE,web.getVisibility());assertNotNull(button(root,"稍后再说"));assertTrue(manager.back());assertEquals(1,root.getChildCount());}
    @Test public void failureAfterForceAllowsLocalTools()throws Exception{force();throwTransport=true;manager.manual();idle();assertFalse(manager.isBlocking());assertEquals(View.VISIBLE,web.getVisibility());assertNotNull(button(root,"继续使用本地功能"));button(root,"继续使用本地功能").performClick();assertEquals(1,root.getChildCount());}
    @Test public void emptyLinkNeverShowsMandatoryView()throws Exception{response=json(installed+10,installed+1,true).put("downloadUrl","").toString();start();assertFalse(manager.isBlocking());assertEquals(View.VISIBLE,web.getVisibility());assertNotNull(button(root,"重试"));assertTrue(manager.back());}
    @Test public void malformedJsonDoesNotCrashOrBlock(){response="not-json";start();assertFalse(manager.isBlocking());assertNotNull(button(root,"继续使用本地功能"));}
    @Test public void timeoutReleasesBlockedViewAndHasRetry()throws Exception{force();executor.hold=true;manager.manual();assertTrue(manager.isBlocking());Shadows.shadowOf(Looper.getMainLooper()).idleFor(13,TimeUnit.SECONDS);assertFalse(manager.isBlocking());assertEquals(View.VISIBLE,web.getVisibility());assertNotNull(button(root,"重试"));}
    @Test public void startupCacheDoesNotBlockOffline()throws Exception{activity.getSharedPreferences("apk-update-native-test",0).edit().putString("apk_config_cache_v1",json(installed+10,installed+1,true).toString()).commit();throwTransport=true;start();assertFalse(manager.isBlocking());assertEquals(View.VISIBLE,web.getVisibility());}
    @Test public void manualCheckWorksWithoutAnyAccountState(){start();button(root,"稍后再说").performClick();int before=requests;manager.manual();idle();assertEquals(before+1,requests);assertNotNull(button(root,"立即更新"));}
    @Test public void browserLaunchUsesSharingPageAndRechecksOnReturn()throws Exception {
        force();ResolveInfo info=new ResolveInfo();info.activityInfo=new ActivityInfo();info.activityInfo.packageName="com.happybox.fixture.browser";info.activityInfo.name="FixtureBrowser";
        Intent browsers=Intent.makeMainSelectorActivity(Intent.ACTION_MAIN,Intent.CATEGORY_APP_BROWSER);
        Shadows.shadowOf(activity.getPackageManager()).addResolveInfoForIntent(browsers,info);
        manager.preferences("{\"vibe\":false,\"dark\":true,\"speed\":\"fast\"}");
        button(root,"立即更新").performClick();Intent opened=Shadows.shadowOf(activity).getNextStartedActivity();assertNotNull(opened);assertEquals(Intent.ACTION_VIEW,opened.getAction());assertEquals("https://test-fixture.lanzou.com/parser-only",opened.getDataString());assertEquals(info.activityInfo.packageName,opened.getPackage());assertEquals(0,feedback);
        int before=requests;manager.onPause();manager.onResume();idle();assertEquals(before+1,requests);assertTrue(manager.isBlocking());assertEquals(View.INVISIBLE,web.getVisibility());
    }
}
