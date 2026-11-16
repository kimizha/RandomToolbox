# 删除音乐板块（取代离线候选版中保留音乐的旧要求）

目标分支 release/happybox-offline，基线 e9d66bcc1c390c822378ac37e013c95c962c3de2；main 和 UI 开发分支不修改。

删除设置页随身音乐卡片、曲目选择、播放/暂停/进度控制、音乐音量及本地状态初始化/保存。删除全部六首 MP3 和目录占位 .gitkeep：ACN Music. - Fooling Mode (1)、Kevin MacLeod - Fluffing a Duck、NewPiano - tricks and traps、Raphaël Beau - Micmacs à la gare、SIDNEY JOSEPH BECHET - Si tu vois ma mère、Ugress - Undead Funeral March。

清除音乐专用 CSS、图标映射、getMusicCover 原生接口及 MediaMetadataRetriever 引用。没有独立播放器第三方依赖或后台服务。共享 toolkit.png 图集包含其他工具素材，不能整张删除，已移除音乐区域的 CSS/JS 使用入口。题库涉及音乐的文字是游戏内容，保留；历史文档和交付报告不是当前运行功能，不删除审计资料。

原工具音效 Web Audio 合成、音效音量、震动、玩法、收藏排序、转盘、本机 JSON 导出、深浅色布局及 APK 更新地址/协议保持不变。不迁移、不清空 localStorage，不主动删除旧音乐偏好键，也不再读取/写入或导出这些失效设置。不更换包名、签名和 SDK 要求；仍使用独立离线 Actions 流程，Release 变体，versionName=3.0，versionCode 由工作流递增。最终签名/版本以本次 Actions verification 为准。

check_offline 测试旧键原样保留、收藏排序/转盘重启保存、所有随机工具实际产生结果、玩法进入、无音乐入口、工具音效 AudioContext、音量及震动设置持久化、320/390/768 宽度深浅色无溢出、返回键、无账号和外部请求。另运行既有聚会 UI、选择界面、纯规则、题库及 APK 更新策略检查。check_offline_apk 检查最终 APK 无音频资源/SDK/探针，并验证包名、递增 versionCode、固定证书、Release 标志。

真机仍需确认：旧版本覆盖安装后数据保留、实际扬声器工具音效及音量、硬件震动、Android 返回与系统浏览器更新跳转。本次不创建 Release、不修改线上 version.json、不向用户推送更新、不操作腾讯云。
