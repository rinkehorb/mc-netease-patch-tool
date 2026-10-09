# Minecraft 网易版 0.2.0.25445 (com.netease.mc.qihoo) —— XML 报错弹窗 溯源与补丁

## 0. 结论先说

那段 `<Code>NoSuchKey</Code>` XML **不是网络请求失败的报错文本，而是服务器真实返回的 HTTP 响应体**，
网易 2017 年那批 CDN 对象已经被删除，阿里云 OSS 对不存在的 Key 返回 **HTTP 404 + 一段 XML 正文**。

游戏里唯一会把「native 传来的 URL」原样塞进 WebView 的地方是：

```
com.mojang.minecraftpe.mcWebViewDialog   （一个 DialogFragment，全屏 WebView）
```

而这个 DialogFragment 在做 `onCreateDialog` 时调用了 `setCancelable(false)`，
并且它等的是 H5 页面里的 JS 通过 `mc.closeMe()` 回调来关闭自己。
页面根本没加载成功，回调永远不来 → 于是表现为 **"弹出 XML + 卡死/必须重启"**。

> 网页请求走的是 WebView 自己的 Chromium 网络栈，
> **完全不经过** `NetUtil` / `AppsFlyerLib` / `iapppay` / `heepay` / `heepay` 这些 Java 类。
> 这就是为什么之前改那些地方"改的地方生效了，XML 照弹"。
> 另外 `AndroidManifest` 删联网权限会导致 SDK 初始化直接异常 → 无限重启，也是同一个原因。

## 1. 溯源证据链

### 1.1 包结构

| 项 | 值 |
|---|---|
| 文件 | `F:\Minecraft ne\Minecraft.apk` |
| 大小 | 157.02 MB (164,650,431 B) |
| classes.dex | 1 个，9,890,560 B，68,337 个字符串，8,704 个类 |
| native | 只有 `lib/armeabi-v7a/`：`libminecraftpe.so` 30.8 MB、`libfmod.so`、`libntunisdk.so`、`libm4399OperateSDKNative.so`、`libcom_netease_androidcrashhandler_AndroidCrashHandler.so` |
| assets | 3,719 项；含完整 H5 启动器 `assets/web/`（`<title>MCPE_H5</title>`） |
| Manifest | `minSdkVersion=19`、`targetSdkVersion=22`、`versionCode=840025445`、`versionName=0.2.0.25445`、application = `com.netease.ntunisdk.application.NtSdkApplication` |
| 未声明 | `extractNativeLibs`（默认 true）、`usesCleartextTraffic`（targetSdk 22 → 默认允许明文 http） |

### 1.2 native 启动器状态机（libminecraftpe.so 字符串表，0x1b70a00 附近）

```
>>>>>>>>>>>>ReqServerlistStage::onAwake()
CdnUrl  TransferServerUrl  WebServerUrl  H5VersionUrl  ChatServerUrl  MomentUrl
ServerStop  UpdateStop  DnsStop
>>>>>>>>>>>>ReqH5VersionStage::onAwake()
>>>>>>>>>>>>InstallAssetStage::onAwake()
StaticWebVersion
_ZN17LoginStateMachine15updateH5VersionEv
_ZN11AppPlatform13getDebugH5UrlEv
_ZN10WebViewMgr11openWebViewERSsSt8functionIFvvEE
web/index.html      file://      file:///android_asset/
```

同一段还有网易的更新/CDN 常量（`g79` 就是网易《我的世界》的项目号）：

```
https://g79.update.netease.com/pack_list/production/g79_packlist
https://g79.update.netease.com/patch_list/production/g79_patchlist
https://g79.update.netease.com/serverlist/adr_release.0.5.json
server_obt / server_qa / server_cbt / server_simu / server_151 ...
```

`obt20171212182501` = **OBT(内测) 构建 2017-12-12 18:25:01**，
这个字符串**在整个 APK 里根本不存在**（全包 3,991 项按字节扫过），
说明 H5/CDN 的基址是运行时由服务器下发的配置决定的 —— 本地改不到字符串。

### 1.3 本地 H5 里直接写着那个域名

`assets/web/static/js/app.99ba093c66352ad3633f.js`：

```js
var i={WebServerUrl:"http://192.168.46.49:10110/index.php",
       SeadraHost:"http://qa.api.pub.seadra.netease.com:8021",
       momentHost:"http://gs-x19.dev.webapp.163.com:8003/",
       FORUM_URL:"http://dev01.gameyw.netease.com:8821"};
"g79.gdl.netease.com"===location.hostname && (i={
       WebServerUrl:"",
       SeadraHost:"https://api.pub.seadra.netease.com/",
       momentHost:"", FORUM_URL:""});
```

即：**这份 H5 是"从 `g79.gdl.netease.com` 上托管"设计的**，
APK 里带的只是兜底副本，且默认配置指向网易内网 `192.168.46.x` 的测试机。
→ 这也预告了「在线模式 UI 不可能救回来」的结局，见第 6 节。

### 1.4 Java 侧唯一入口（smali）

```
libminecraftpe.so
   └─ JNI: MainActivity.openWebview(ILjava/lang/String;)V        <-- .so 里有该签名串
        ├─ isopen==1 -> MainActivity$23.run()
        │                   └─ MainActivity.showWebviewDialog(url)
        │                        ├─ 已显示 -> mcWebViewDialog.load_url(url)
        │                        └─ 未显示 -> mcWebViewDialog.set_loadurl(url)
        │                                     + show_a(getFragmentManager(),"WebviewDialog")
        └─ isopen!=1 -> MainActivity$24.run()          （关闭）

mcWebViewDialog.onStart()          -> 全屏 window
mcWebViewDialog.onCreateDialog()   -> setCancelable(false)
mcWebViewDialog.onCreateView()     -> initWebview() + loadUrl(m_loadurl)
mcWebViewDialog.initWebview()      -> addJavascriptInterface(this,"mc")
mcWebViewDialog.closeMe()          -> dismiss()      @JavascriptInterface  <-- 唯一正规关闭通道
mcWebViewClient.onReceivedError()  -> 载入 file:///android_asset/storge/asset/networkerror.html
```

关键点：`onReceivedError` **只在网络层失败（DNS/连接）时触发**。
HTTP 404 属于"请求成功、内容是错误页"，**不触发** `onReceivedError`，
Chromium 老老实实把那段 XML 当文档渲染出来 → 就是你看到的弹窗。

## 2. 补丁内容（只动 Java，不碰 .so，不重编译资源）

| # | 文件 | 改动 | 作用 |
|---|---|---|---|
| A1 | `com/mojang/minecraftpe/mcWebViewClient.smali` | 新增 `onReceivedHttpError(WebView, WebResourceRequest, WebResourceResponse)`，仅当 `request.isForMainFrame()` 且状态 ≥400 时载入本地 `file:///android_asset/storge/asset/networkerror.html` | API 23+ 在 HTTP 层直接掐掉 XML 渲染 |
| A2 | 同上 | `onPageFinished` 注入一次性 JS 守卫（新字段 `injected:Z`）：检测到 `nosuchkey` / `aliyuncs.com` / `<error>` / `specified key does not exist` 就把页面整体替换成中文友好页 + 「关 闭」按钮，按钮调用游戏**自己的** `mc.closeMe()` | 覆盖 API 19–22，以及"XML 以 HTTP 200 返回"的情况 |
| B | `com/mojang/minecraftpe/mcWebViewDialog.smali` | `setCancelable(false)` → `true` | 逃生口 |
| C | `com/mojang/minecraftpe/mcWebViewDialog$1.smali` | BACK 键在 `nativeWebviewBackPressed()` 之后追加一次 `dismiss()` | 保证任何情况下都能按返回键关掉弹窗 |

**刻意没做的事**

* 没碰 `libminecraftpe.so`（30 MB ARM 库，本机无 Ghidra/IDA，盲改风险远大于收益）
* 没让 `showWebviewDialog` 直接 return（native 在等 H5 的 JS 回调，
  硬掐掉大概率变成"连弹窗都没有但照样卡死"，比现在还糟）
* 没改 `targetSdkVersion`（提到 23+ 会引入运行时权限/存储/明文流量等一连串行为变更，
  2017 年的游戏极可能直接崩；而且你的机器本来就能装 targetSdk 22 的包）
* 没删 `INTERNET` 权限（已验证会导致无限重启）

## 3. 构建结果与自检

```
原始 classes.dex   9,890,560 B   string 68337  type 10254  proto 13038  field 33311  method 64856  class 8704
补丁 classes.dex   9,891,876 B   string 68341  type 10254  proto 13038  field 33312  method 64858  class 8704
                                (+4 string / +1 field / +2 method / 类数不变)

重打包后：
  testzip                     OK
  条目数                      3991（3988 复制 + 3 个新签名文件）
  缺失条目                    无
  除 classes.dex 外内容差异    无
  resources.arsc              与原包逐字节相同
  AndroidManifest.xml         与原包逐字节相同
  lib/armeabi-v7a/*.so        与原包逐字节相同
  未压缩条目                  3296 个，全部 4 字节对齐（zipalign 等价）
  classes.dex                 == 补丁 dex（sha256 7e3d504c…）
  APK sha256                  f6b1c3af05878ff12d55c3728c4587849cdd00cfec3639bca8fd3075bf9e327e
  签名                        v1 + v2 + v3 全部 verify 通过
```

反向验证：把签名后的 APK 重新 baksmali 出 **8,704 个 smali 文件**（无一失败），
确认 `onReceivedHttpError` / `injected` / JS 字符串 / `setCancelable` / `dismiss()` 都在。
注入的 JS 从 dex 里按字节还原后与设计完全一致（1028 字节，中文完好，
不含 `"` `#` `\` 等会干扰 `javascript:` URL 解析的字符）。

## 4. 安装

```powershell
# 必须卸载原版：换了签名，无法覆盖安装
adb uninstall com.netease.mc.qihoo
adb install -r "Minecraft-0.2.0.25445-offline-patched.apk"
```

或直接手机端点安装包（记得先卸载原版，**不要把原版的存档删了**——
存档在 `/sdcard/games/com.netease.mc.qihoo/` 和 `Android/data/com.netease.mc.qihoo/`，
卸载前先备份出来，装完再放回去）。

安装后预期：联网状态下启动，原本弹 XML 的那个全屏弹窗变成一张中文提示页，
点「关 闭」或按返回键即可关掉，随后正常进入离线游玩。

## 5. 兜底方案：物理/系统级断网（比改包更稳）

如果补丁在你机器上还有残留问题，用第 7 节的 `hosts_netease_block.txt`
把网易那批已经下线的域名黑洞掉，效果等价于"WiFi 开着但游戏以为没网"，
也就是**你已经验证过可以正常玩**的那条分支。详见《网络屏蔽指南.md》。

## 6. 关于"调出在线模式 UI"——为什么做不到

必须说实话：**这个包的在线模式已经不可能恢复了**，不是改包能解决的问题。

1. 那批资源在服务端已被删除。`g79.gdl.netease.com/obt20171212182501/...`
   返回的是 OSS 的 `NoSuchKey`，也就是**对象真的不存在**了，不是权限或路径问题。
2. 本地 `assets/web/` 那份 H5 是**开发版**：它判断 `location.hostname === "g79.gdl.netease.com"`
   才切到生产配置，否则用内网地址 `http://192.168.46.49:10110/index.php`
   和 `http://qa.api.pub.seadra.netease.com:8021`。
   从 `file:///android_asset/web/index.html` 加载时 hostname 为空 → 走内网配置 → 必然失败。
3. 就算把 JS 里的配置硬改成生产地址，生产地址本身也已经下线；
   登录、服务器列表、资源下载、充值全部没有后端。
4. 单机/离线世界是纯本地逻辑（`libminecraftpe.so` 里的 Bedrock 引擎），
   跟这些接口无关，所以它能正常玩——这也正好解释了"断网反而一切正常"。

**能拿到的最好结果**就是本补丁：不再弹 XML、不再卡死、联网状态下照常离线游玩。

## 7. 复现 / 自己重打的完整步骤

环境里原本**没有 JDK、没有 apktool、没有 Android SDK**，全部是现拉的：

```powershell
# 工具（都放在 mc-re\tools\）
Temurin JRE 17 (Adoptium)                    -> tools\jre\
baksmali-2.5.2.jar / smali-2.5.2.jar         -> bitbucket.org/JesusFreke/smali/downloads/
uber-apk-signer-1.3.0.jar                    -> github.com/patrickfav/uber-apk-signer

# 1) 拆 dex（只拆 dex，不用 apktool 碰资源）
java -Xmx4g -jar tools\baksmali.jar disassemble original\classes.dex -o smali

# 2) 打补丁（幂等，可重复跑）
python 01_patch_smali.py

# 3) 汇编回 dex
java -Xmx6g -jar tools\smali.jar assemble smali -o patched\classes.dex

# 4) 只替换 classes.dex，其余条目逐字节原样复制 + 4 字节对齐
python 02_build_apk.py

# 5) 签名（注意必须加 -Djava.io.tmpdir，否则 uber-apk-signer 写临时密钥库会被拒绝访问）
java "-Djava.io.tmpdir=JtmpDir" -jar tools\uber-apk-signer.jar `
     -a patched\Minecraft-unsigned.apk -o patched\signed --allowResign --skipZipAlign --verbose
```

`01_patch_smali.py` / `02_build_apk.py` 就是"补丁脚本"，`03_sign_apk.ps1` 是签名步骤。
三个脚本都带自检输出。

## 8. 风险与注意事项

| 风险 | 说明 |
|---|---|
| 换签名 | 无法覆盖安装原版，必须先卸载；**先备份存档** |
| 签名校验 | 网易/360 SDK 部分逻辑会读 `GET_SIGNATURES`。你之前的改包能跑起来，说明这游戏对签名不敏感；若启动即闪退，请回退到第 5 节的 hosts 方案（不改包） |
| Android 14/15 | 系统会拒绝安装 `targetSdkVersion < 23` 的应用。这个包是 22，所以**原版也一样装不上**。你的手机能跑原版，说明 ≤ Android 13，本补丁同为 22，行为一致 |
| 在线功能 | 依然是彻底不可用（后端已下线），补丁只保证"不弹 XML + 不卡死" |
| 未实机验证 | 本环境**没有连接任何 Android 设备**（`adb devices` 为空），也跑不动 ARM 模拟器。以上结论来自静态逆向 + 打包自检，**最终需要你在手机上装一次确认** |

## 9. 验证清单（装好后请照着看）

1. 联网启动游戏，几秒后原本的 XML 弹窗 → 应变成中文提示页。
2. 点「关 闭」→ 弹窗关闭；再启动一次，按**返回键** → 弹窗也应关闭。
3. 关掉弹窗后能否进入离线世界正常玩。
4. 若第 2 步按返回键仍关不掉，说明该弹窗不是 `mcWebViewDialog`，
   请把 `/sdcard/Android/data/com.netease.mc.qihoo/files/` 下的日志或
   `logcat | grep -iE "MinecraftPE|MCPE|seayoung|WebviewMgr"` 发我。
   （`seayoung` 是这些 WebView 类的作者留下的 TAG，很好过滤。）

---

# v2 补丁（2026-10-08）—— 不弹窗，直接进离线游玩

## 0. v1 实测反馈
联网启动：XML 闪一下 → 变成一张全屏页 "哎呀！网络不给力呀！"（这是 APK 自带的
`assets/storge/asset/networkerror.html`，被 v1 的 onReceivedHttpError 载入），
页面没有自动退出机制，人被卡在这张错误页上。

## 1. v2 改了什么（仍然只动 Java 层，不碰 .so、不重编译资源）
| # | 文件 | 改动 | 作用 |
|---|---|---|---|
| A1 | mcWebViewClient.smali | onReceivedHttpError：主文档 ≥400 不再载错误页，改为注入 JS 自动关闭 | API23+ 掐掉 XML/错误页停留 |
| A2 | 同上 | onPageFinished 每次注入 JS 守卫：命中 nosuchkey / aliyuncs.com / `<error>` / specified key does not exist / 网络不给力(\u7f51…) → mc.autoClose() | 覆盖 API19–22、HTTP 200 返回 XML、以及 H5 启动器自己的错误页 |
| B | mcWebViewDialog.smali | setCancelable(true)；新增 @JavascriptInterface autoClose() | 逃生口 + 自动关闭通道（切 UI 线程） |
| B3 | mcWebViewDialog$4.smali（新类） | Runnable：nativeWebviewBackPressed() + dismiss() | 等价"用户按返回键" |
| C | mcWebViewDialog$1.smali | BACK 键：通知 native 后追加 dismiss() | 保证一定能关 |
| D | MainActivity$23.smali | URL 门卫：url 含 netease.com / aliyuncs.com → 直接 nativeWebviewBackPressed()，不弹 WebView | 联网启动零弹窗、零闪烁 |
| E | MainActivity.smali | hideWebview 增加 null/isAdded 保护 | 防止"从未 show 的 DialogFragment 被 dismiss"崩溃 |

核心逻辑：native 的关闭通道是 `nativeWebviewBackPressed()`（返回键信号），
它之后 native 会自行 openWebview(0) → hideWebview() → dismiss()。
所以所有"自动关闭"都走这条通道，native 会像用户按了返回键一样继续进入离线游玩。

## 2. 构建与自检
```
原始 classes.dex   9,890,560 B  string 68337  type 10254  proto 13038  field 33311  method 64856  class 8704
v2   classes.dex   9,891,600 B  string 68343  type 10255  proto 13038  field 33312  method 64861  class 8705
                          (+6 string / +1 type / +1 field / +5 method / +1 class)
新增：onReceivedHttpError、autoClose、mcWebViewDialog$4（<init> + run）
重打包自检：testzip OK；条目 3991（3988 复制 + 3 新签名文件）；缺/多条目 无；
           除 classes.dex 外内容差异 无；resources.arsc / AndroidManifest / lib/*.so 原样；
           未压缩条目 3296 个全部 4 字节对齐；签名 v1+v2+v3 verify 通过。
证书指纹（SHA-256）：1e08a903aef9c3a721510b64ec764d01d3d094eb954161b62544ea8f187b5953
           —— 与 v1 完全一致，可直接 adb install -r 覆盖安装 v1。
反向验证：最终 APK 的 dex 重新 baksmali 出 8705 个类，全部补丁点核对在位；
          两条注入 JS 从 dex 逐字节还原 == 设计稿（守卫 406B / 自动关闭 67B）。
APK sha256：aba41e602fa3ad61963cd26517fd16e17c36d2881013bba2c4c69bcbd89d9e6d
```

## 3. 安装
签名与 v1 相同：
- 若手机当前装的是 v1 补丁版：直接覆盖安装本包即可，无需卸载。
- 若退回装过原版：先卸载原版再装（会清数据，先备份存档
  `/sdcard/games/com.netease.mc.qihoo/` 与 `Android/data/com.netease.mc.qihoo/`）。

## 4. v2 验证清单
1. 联网启动：应【完全不出现】XML、也不出现 "哎呀！网络不给力呀！"，几秒内直接进入游戏。
2. 若仍看到任何弹窗闪一下：应自动消失（自动按返回键逻辑），随后进入游戏。
3. 断网启动：应和之前一样正常进离线世界（该路径未改动）。
4. 万一仍有残留弹窗关不掉：返回键兜底（v2 里返回键=通知 native + 主动 dismiss）；
   仍不行再把 `logcat | grep -iE "MinecraftPE|MCPE|seayoung|WebviewMgr"` 发我。

---

# v3 补丁（2026-10-08）：移除 360 悬浮球 + 默认皮肤/名字改为 Steve(rinkehorb)

## 0. 结论先说
1. **360 悬浮球（点开是"加速/福利/实名制"）已整体移除**：根因是 360 Matrix SDK 初始化时
   依次调用了 `QSuspendAgent.init`、`suspend/c/c.l()`、`support/gameunionplugin/a.a(Context)`
   （360 游戏中心插件，悬浮球菜单就来自它）。v3 在 `com/qihoo/gamecenter/sdk/matrix/a.smali`
   的 `c(Activity, MatrixCallBack)` 里把这 3 处调用全部 NOP 掉。悬浮球不再出现，
   点菜单项才触发的 `assets/360sdk_res` 资源缺失报错也随之消失（该报错来自
   `matrix/a.smali` 的 `h(Activity)`：`QcoinUtil.setResFullPath("360sdk_res/res_580_7.dat")`，
   包内本就无此资源，是"点击菜单项→打开 360 支付/游戏中心页→缺资源"的连锁反应）。
   已确认 Manifest 中没有独立的"浮窗 Service"，悬浮球纯由 Java 初始化链拉起，NOP 即断根。

2. **默认皮肤与玩家名已改为 rinkehorb / 经典 Steve 外观**：
   - 皮肤包数据 `assets/resource_packs/skins/skinpacks/Base/skindefs.json` 重排：
     Steve 条目排第一位（默认选中），名字字段由 "Steve" 改为 "rinkehorb"；
     Alex 条目同步改造为"Steve 外观 + 名字 rinkehorb"（geometry 换 classic、
     texture 指向 steve），并保留 id `skinpacks/Base/alex` —— 双保险，
     即使引擎按硬编码皮肤 id 选中默认，结果也是 Steve 外观 + rinkehorb 名。
   - `alex.png` / `alex_dev.png` 字节级替换为 `steve.png` / `steve_dev.png` 内容（第三道保险）。
   - 网易版离线玩家名跟随"默认选中皮肤"的名字（`_setting::on_create_role` /
     `get_selected_skin_information` 链路），所以改名 = 改 skindefs.json 的名字字段。

## 1. 改动清单
| # | 位置 | 改动 |
|---|---|---|
| A | `com/qihoo/gamecenter/sdk/matrix/a.smali` | 3 处调用 NOP（QSuspendAgent.init / c.c.l() / gameunionplugin init） |
| B | `assets/resource_packs/skins/skinpacks/Base/skindefs.json` | Steve 第一 + 名字 rinkehorb；Alex 条目改造为 Steve 外观 + rinkehorb |
| C | `assets/resource_packs/skins/skinpacks/Base/alex.png` / `alex_dev.png` | 替换为 steve.png / steve_dev.png 内容 |

刻意没做：
* 没动 `libminecraftpe.so`（ARM 库盲改风险大）；
* 没动其他 12 个皮肤包（Biome2/CampfireTales/JTTW 等共 222 张皮肤全部保留，
  需要删包瘦身可另说）；
* 没动在线功能（本就不可用）。

## 2. 构建结果与自检
```
classes.dex:  9,891,584 B（原 9,890,560 / v2 9,891,600）
smali 反向验证: baksmali 全部成功；3 处目标调用残留 = 0；nop 计数 5
重打包后:
  testzip                  OK
  条目数                   3988（复制）+ 3 个新签名文件
  缺失/多出条目            无
  非预期条目差异            无（除 classes.dex 与 3 个指定皮肤资源外全部原样）
  预期替换条目差异          全部与设计一致
  resources.arsc           与原包逐字节相同
  AndroidManifest.xml      与原包逐字节相同
  lib/armeabi-v7a/*.so     与原包逐字节相同
  未压缩条目 3296 个        全部 4 字节对齐
  签名                     v1 + v2 + v3 全部 verify 通过
  证书 SHA256              1e08a903…（与 v2 完全相同 → 可直接覆盖安装，无需卸载）
  APK sha256               cccb46606510b5d6d3b4390f7989f9f0a974e9bda06abb402d4fdd41836a7736
```

## 3. 安装
**与 v2 同一签名，可以直接覆盖安装，存档不动：**
```
adb install -r Minecraft-0.2.0.25445-offline-v3.apk
```
或把 APK 传到手机直接覆盖安装（同一签名 → 允许覆盖；若系统提示签名不一致，
说明装的是更早版本，卸载前先备份存档）。

## 4. 验证清单
1. 联网启动游戏：360 悬浮球不再出现（此前点开是 加速/福利/实名制）。
2. 进离线/单机世界：玩家名为 **rinkehorb**，角色为经典 Steve（粗手臂）外观。
3. 联网时的"哎呀！网络不给力呀！"页与 XML 弹窗行为与 v2 一致（v2 已实测 OK）。
4. 若名字仍显示 Alex（说明你机器上存过旧的 options.txt/旧世界数据），
   删除旧世界或清掉 `files/` 下旧配置再进新世界。

## 5. 关于"插件式改皮肤/改名"的结论（调研记录）
用户提出"放文件重启生效"的插件式诉求。调研结论：
* 引擎保留了 `ResourcePackRepository` / `DirectoryPackSource` 外部扫描符号，
  `.so` 内硬编码 `/games/com.netease/resource_packs`、`options.txt`、`mp_username`；
* 但 `MainActivity.getExternalStoragePath()` 返回 `getExternalFilesDir(null)`
  （= /sdcard/Android/data/com.netease.mc.qihoo/files/），且用户实机在外部目录
  找不到 minecraftWorlds/resource_packs/options.txt —— 说明该 0.2.0 网易包
  实际数据目录位置不明/外部目录机制未实际落地（Android 11+ 还默认隐藏
  Android/data）。因此"外部放文件即生效"路线在本包不成立，退回"APK 内置"方案。
* 皮肤包路径证据：`resource_packs/skins/skinpacks/...`（.so 字符串）+ 内置
  13 包 222 张皮肤；网易版皮肤列表由 H5/服务器驱动（已下线），本地仅 assets 生效。
