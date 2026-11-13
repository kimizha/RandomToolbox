# 开心盒离线发布候选版

基于 UI 分支远程最新提交 90bf3c783e6d8f8a6a31c936b82be3a7dcbf30de，新建 release/happybox-offline。原开发分支及 main 不变。

运行资产不再注入账号、CloudBase SDK、同步、资料或探针。历史云函数、部署 ZIP、旧账号脚本和文档保留用于审计，不被离线工作流或 APK 引用。旧构建工作流禁止在此分支执行，独立离线工作流不含发布步骤。

继续沿用 appassets.androidplatform.net 的 HTTPS WebView 来源、applicationId、minSdk、targetSdk、DOM Storage 和全部 rt_ 本地键。启动不迁移、不清空、不删除原账号缓存。已在本机的数据保持原样，历史多收藏顺序不截断，新增上移/下移排序。原只支持当前转盘选项编辑的行为保持不变，未凭空声称已存在多转盘库。账号缓存中未落入当前配置的数据仍在原键中，可导出 JSON；不会自动覆盖当前配置。仅云端存储且未下载的数据不在离线版内，不能声称已迁移。

版本名 3.0，离线 CI versionCode=200000+本工作流运行序号。原固定签名必须匹配已交付 100160/100161 证书 SHA-256：714524c73030e3d5010c849f52012af5adc7f36ecc2b0013ec6bff4c8324fa4b。缺失或不符时停止提供 APK，不使用临时证书。构建 assembleRelease，测试 testDebugUnitTest；不会创建 GitHub Release。未来跨分支发包也必须高于已安装版本。

内置六个音乐资源原字节保留，设置页增加本地曲目选择、系统播放控制和独立音乐音量。工具音效、震动、深色模式、动画设置保留。APK 更新的原生实现、远程地址和 version.json 未修改，联网能力仅为更新及用户主动打开的外部页面保留。不启用账号、云同步或设备限制。

自动检查：check_offline.py 测试实际打包 HTML，在阻断所有外部请求情况下启动、旧键原样保留、排序/转盘/主题/音乐设置重启持久化、全部工具玩法进入、返回键和 JSON 导出；check_party_core、check_game_library、check_apk_updates 保留。check_offline_apk 检查最终 APK 不含账号/SDK/探针，并逐字节核对音乐。

待真机验收：同签名覆盖安装后的 WebView 数据、原生文件导出、真实扬声器播放/音效、震动、横竖屏、返回键、系统浏览器及更新断网/恢复、所有玩法完整流程。浏览器模拟和构建成功不能替代这些验收。安装前推荐在旧版本导出 JSON；直接覆盖安装，不要卸载旧版。

修改范围：两份工作流、app/build.gradle、MainActivity.java、index.html、ui/offline.js、ui/local-backup.js、scripts/local-backup.js、签名准备及验证、离线回归/签名/APK 检查脚本和本文档/测试记录。没有修改腾讯云或线上更新文件。

本地回归结果：离线专项 40 项（含六种随机工具真实产生结果）、聚会 UI 123 项、选择 UI 51 项、纯规则 25 项、APK 更新策略 55 项全部通过，题库校验通过。完整记录见 docs/offline。原生测试及最终 APK 元数据以对应 Actions 的 XML/verification.json 为准。首次构建未上传 APK：校验脚本未兼容 Android ZIP 的 UTF-8 路径标记；已修复仅用于核对的名称解码，音乐资源未修改。

最终候选构建成功：https://github.com/kimizha/RandomToolbox/actions/runs/43428504255。APK 为 Release 变体，versionName=3.0，versionCode=200003，源提交 b118fc4249100a83467c3a3ac9470e40f96a9163。签名与已交付版本一致，并实际对比仓库已有 2.7 APK 的包名/签名/递增版本；与 100161 的覆盖安装仍须真机验证。后续仅测试及交付记录提交，不改变此 APK 的运行资产。完整元数据、改动清单见 docs/offline/delivery.json、changed-files.txt。未创建 Release。
