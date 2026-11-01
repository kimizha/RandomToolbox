package com.randomtoolbox.app;

import java.net.URI;
import org.json.JSONObject;
import org.json.JSONTokener;

/** Validated APK-only remote configuration. Does not know about accounts or web assets. */
public final class ApkUpdatePolicy {
    public enum Decision { NONE, OPTIONAL, FORCED }
    public static final class Config {
        public final long latestCode, minimumCode, intervalMillis;
        public final boolean force;
        public final String latestName, downloadUrl, title, message;
        private Config(long latest, String name, long minimum, boolean force, String url, String title, String message, long hours) {
            this.latestCode=latest; this.latestName=name; this.minimumCode=minimum; this.force=force;
            this.downloadUrl=url; this.title=title; this.message=message; this.intervalMillis=hours*3600000L;
        }
        public Decision decide(long actualApkCode) {
            if (actualApkCode >= latestCode) return Decision.NONE;
            if (!validDownloadUrl(downloadUrl)) throw new IllegalArgumentException("Download page is not configured");
            return force && actualApkCode < minimumCode ? Decision.FORCED : Decision.OPTIONAL;
        }
    }
    public static Config parse(String raw) throws Exception {
        if (raw == null || raw.length() > 32768) throw new IllegalArgumentException("Configuration too large");
        JSONTokener tokener=new JSONTokener(raw);JSONObject j=new JSONObject(tokener);if(tokener.nextClean()!=0)throw new IllegalArgumentException("Trailing JSON content");
        long latest=integer(j,"latestVersionCode",1,2100000000L);
        long minimum=integer(j,"minSupportedVersionCode",1,latest);
        long hours=integer(j,"checkIntervalHours",1,168);
        Object force=j.get("forceUpdate");
        if (!(force instanceof Boolean)) throw new IllegalArgumentException("forceUpdate must be boolean");
        String name=text(j,"latestVersionName",40,false), url=text(j,"downloadUrl",2048,true);
        if ((Boolean)force && url.isEmpty()) throw new IllegalArgumentException("Force requires a configured download page");
        if (!url.isEmpty() && !validDownloadUrl(url)) throw new IllegalArgumentException("Invalid download page");
        return new Config(latest,name,minimum,(Boolean)force,url,text(j,"updateTitle",80,false),text(j,"updateMessage",4000,false),hours);
    }
    private static long integer(JSONObject j,String key,long min,long max) throws Exception {
        Object o=j.get(key);
        if (!(o instanceof Number) || !o.toString().matches("-?\\d+")) throw new IllegalArgumentException(key+" must be an integer");
        long n=Long.parseLong(o.toString());if(n<min||n>max)throw new IllegalArgumentException(key+" out of range");return n;
    }
    private static String text(JSONObject j,String key,int max,boolean allowEmpty) throws Exception {
        Object o=j.get(key);if(!(o instanceof String))throw new IllegalArgumentException(key+" must be text");
        String s=((String)o).trim();if(s.length()>max||(!allowEmpty&&s.isEmpty()))throw new IllegalArgumentException(key+" invalid length");return s;
    }
    public static boolean validDownloadUrl(String text) {
        try {
            if(text==null||text.length()>2048||text.matches("(?s).*\\s.*"))return false;
            URI u=new URI(text);String host=u.getHost();
            if(!"https".equalsIgnoreCase(u.getScheme())||host==null||u.getRawUserInfo()!=null||(u.getPort()!=-1&&u.getPort()!=443)||u.getRawPath()==null||u.getRawPath().length()<2)return false;
            // Official sharing domains and their subdomains; never accept a suffix lookalike.
            return host.toLowerCase(java.util.Locale.ROOT).matches("(?:[a-z0-9-]+\\.)*(?:lanzou[a-z]?\\.com|lanzn\\.com|lanznu\\.com|woozooo\\.com)");
        } catch(Exception e){return false;}
    }
    public static long retryDelay(int failures){return Math.min(900000L,60000L*(1L<<Math.max(0,Math.min(4,failures))));}
    /** UI-independent lifecycle state, also used by JVM regression tests. */
    public static final class Session {
        public volatile boolean checking, blocking, offline;
        public Config config;
        public long lastSuccessAt;
        private long generation;
        public long begin() { if(checking)return 0;checking=true;return ++generation; }
        public boolean success(long token,Config c,long current,long now) {
            if(token!=generation||!checking)return false;
            Decision d=c.decide(current);config=c;lastSuccessAt=now;checking=false;offline=false;blocking=d==Decision.FORCED;return true;
        }
        public boolean failure(long token) {
            if(token!=generation||!checking)return false;
            checking=false;offline=true;blocking=false;generation++;return true;
        }
        public void networkLost(){generation++;checking=false;offline=true;blocking=false;}
        public boolean mayDismiss(){return !blocking;}
        public boolean due(long now){return config==null||now<lastSuccessAt||now-lastSuccessAt>=config.intervalMillis;}
    }
    private ApkUpdatePolicy() {}
}
