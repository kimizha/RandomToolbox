package com.randomtoolbox.app;
import org.json.JSONObject;

/** Offline executable tests against the exact policy/session classes used by Android. */
public final class ApkUpdatePolicyTest {
    private static int checks;
    private static void check(String name,boolean condition){if(!condition)throw new AssertionError(name);checks++;System.out.println("PASS "+name);}
    // These are parser fixtures only, never shipped as a configured download URL or opened.
    private static JSONObject config(long latest,long minimum,boolean force) throws Exception {
        return new JSONObject().put("latestVersionCode",latest).put("latestVersionName","3.0")
            .put("minSupportedVersionCode",minimum).put("forceUpdate",force)
            .put("downloadUrl","https://test-fixture.lanzou.com/parser-only")
            .put("updateTitle","开心盒更新").put("updateMessage","更新说明").put("checkIntervalHours",6);
    }
    private static ApkUpdatePolicy.Config parse(JSONObject c)throws Exception{return ApkUpdatePolicy.parse(c.toString());}
    private static void bad(String name,JSONObject c){boolean rejected=false;try{parse(c);}catch(Exception e){rejected=true;}check(name,rejected);}
    public static void main(String[] args) throws Exception {
        ApkUpdatePolicy.Config ordinary=parse(config(100200,100200,false)),forced=parse(config(100200,100180,true));
        check("Latest APK is not blocked",forced.decide(100200)==ApkUpdatePolicy.Decision.NONE);
        check("APK newer than remote latest is not blocked",forced.decide(100250)==ApkUpdatePolicy.Decision.NONE);
        check("Ordinary update has no minimum-version block",ordinary.decide(100155)==ApkUpdatePolicy.Decision.OPTIONAL);
        check("Force requires below minimum",forced.decide(100179)==ApkUpdatePolicy.Decision.FORCED);
        check("Minimum version itself is optional",forced.decide(100180)==ApkUpdatePolicy.Decision.OPTIONAL);
        check("Web resource version is not part of the decision",forced.decide(100155)==ApkUpdatePolicy.Decision.FORCED);
        check("Remote emergency switch changes forced to ordinary",parse(config(100200,100180,false)).decide(100155)==ApkUpdatePolicy.Decision.OPTIONAL);
        bad("Missing code rejected",config(100200,100180,true).put("latestVersionCode",JSONObject.NULL));
        bad("String version code rejected",config(100200,100180,true).put("latestVersionCode","100200"));
        bad("Fractional version code rejected",config(100200,100180,true).put("latestVersionCode",100200.5));
        bad("Minimum above latest rejected",config(100200,100201,true));
        bad("Negative code rejected",config(-1,1,false));
        bad("String force flag rejected",config(100200,100180,true).put("forceUpdate","true"));
        bad("Check interval zero rejected",config(100200,100180,true).put("checkIntervalHours",0));
        bad("Unbounded interval rejected",config(100200,100180,true).put("checkIntervalHours",169));
        bad("Empty force download URL cannot enable force",config(100200,100180,true).put("downloadUrl",""));
        ApkUpdatePolicy.Config unconfigured=parse(config(100155,100155,false).put("downloadUrl",""));
        check("Blank URL and disabled force safe for a new APK",unconfigured.decide(100156)==ApkUpdatePolicy.Decision.NONE);
        boolean noOffer=false;try{unconfigured.decide(100154);}catch(Exception e){noOffer=true;}check("Blank URL cannot offer a broken update to older APK",noOffer);
        for(String u:new String[]{"http://test.lanzou.com/i1","javascript:alert(1)","file:///tmp/app.apk","https://evil.example/app","https://lanzou.com.evil.example/i1","https://lanzou.com@evil.example/i1","https://evil.example@lanzou.com/i1","https://lanzou.com:444/i1","https://lanzou.com/","https://test.lanzou.com/i1\n"})check("Reject unsafe URL: "+u.replace('\n',' '),!ApkUpdatePolicy.validDownloadUrl(u));
        for(String u:new String[]{"https://test.lanzou.com/parser-only","https://www.lanzoui.com/parser-only","https://abc.lanzn.com/parser-only?pwd=fixture","https://abc.lanzoux.com/parser-only"})check("Allow official HTTPS sharing domain",ApkUpdatePolicy.validDownloadUrl(u));
        boolean malformed=false;try{ApkUpdatePolicy.parse("{broken");}catch(Exception e){malformed=true;}check("Malformed JSON rejected",malformed);
        boolean trailing=false;try{ApkUpdatePolicy.parse(config(100200,100180,true)+" trailing");}catch(Exception e){trailing=true;}check("Trailing garbage rejected",trailing);
        bad("Oversized title rejected",config(100200,100180,true).put("updateTitle","x".repeat(81)));
        ApkUpdatePolicy.Session s=new ApkUpdatePolicy.Session();
        check("No configuration never locks a fresh install",!s.blocking&&s.mayDismiss());
        long one=s.begin();check("Concurrent request is coalesced",s.begin()==0);
        check("Offline failure releases request and permits local tools",s.failure(one)&&!s.checking&&!s.blocking&&s.offline&&s.mayDismiss());
        long two=s.begin();check("Fresh forced response blocks",s.success(two,forced,100155,1000)&&s.blocking&&!s.mayDismiss());
        check("Ordinary page navigation cannot clear native forced state",s.blocking&&!s.mayDismiss());
        long three=s.begin();check("Returning from download keeps restriction during recheck",s.blocking&&s.checking);
        check("Installed old APK still forced on return",s.success(three,forced,100155,2000)&&s.blocking);
        long four=s.begin();check("Emergency remote off removes forced restriction",s.success(four,ordinary,100155,3000)&&!s.blocking&&s.mayDismiss());
        long five=s.begin();s.success(five,forced,100155,4000);s.networkLost();check("Network loss releases restriction immediately",!s.blocking&&!s.checking&&s.offline);
        long six=s.begin();check("Network recovery can refresh remote policy",s.success(six,ordinary,100155,5000)&&!s.blocking);
        long stale=s.begin();s.failure(stale);long fresh=s.begin();s.success(fresh,ordinary,100155,6000);
        check("Timed-out forced response cannot override emergency-off response",!s.success(stale,forced,100155,7000)&&!s.blocking);
        check("Automatic interval honored after success",!s.due(6001));check("Periodic refresh becomes due",s.due(6000+ordinary.intervalMillis));check("Clock rollback triggers fresh check",s.due(1));
        ApkUpdatePolicy.Session cached=new ApkUpdatePolicy.Session();cached.config=forced;check("Cached force config alone cannot lock an offline launch",!cached.blocking&&cached.mayDismiss());
        long timeout=cached.begin();cached.failure(timeout);check("Timeout never leaves checking forever",!cached.checking&&!cached.blocking);
        check("Manual/new startup check is independent of login",cached.begin()!=0);
        check("Failure backoff starts at one minute",ApkUpdatePolicy.retryDelay(0)==60000);
        check("Failure backoff grows without repeated tight polling",ApkUpdatePolicy.retryDelay(1)==120000&&ApkUpdatePolicy.retryDelay(2)==240000);
        check("Failure backoff is bounded at fifteen minutes",ApkUpdatePolicy.retryDelay(Integer.MAX_VALUE)==900000);
        System.out.println(checks+" APK policy and lifecycle checks passed");
        if(args.length>0){ApkUpdatePolicy.Config actual=ApkUpdatePolicy.parse(java.nio.file.Files.readString(java.nio.file.Path.of(args[0])));System.out.println("Repository version.json validated: latest="+actual.latestCode+", minimum="+actual.minimumCode+", force="+actual.force+", downloadConfigured="+!actual.downloadUrl.isEmpty());}
    }
}
