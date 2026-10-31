# 随机工具箱 Android

A 版（首页一大两小常用工具布局）的离线 WebView 安卓项目。

GitHub Actions → Build Android APK → Run workflow，构建成功后下载 Artifacts 中的 APK。

注意：生成的是调试签名 APK，仅用于个人测试。正式发布时需要稳定的发布签名、提高 targetSdk 并做安全与兼容性适配。

UI 开发分支的账号恢复及固定签名说明：[docs/ACCOUNT-SYNC.md](docs/ACCOUNT-SYNC.md)。此分支缺少固定签名 Secrets 时仅编译检查，不发布临时签名 APK。
