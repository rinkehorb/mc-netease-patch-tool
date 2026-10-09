# MC 一键修改器（MCPatchTool）

给网易《我的世界》APK 换名字 / 换皮肤（含细粗手臂）/ 换资源包的小工具。
**全程在手机本地完成，不联网、不上传**，产出直接签好名的 APK，点一下就能装。

---

## 0. 交付物清单

| 路径 | 说明 |
|---|---|
| `MCPatchTool-v1.0.apk`（工作区根目录，208 KB） | **装到手机上就能用的工具**，已用内置密钥签好名 |
| `app/build/outputs/apk/release/app-release.apk` | Gradle 构建的同一产物 |
| `build/manual/` → `manual-build/MCPatchTool.apk` | 免 Gradle 手工构建的产物（签名一致） |
| `app/src/main/java/com/mctool/mcpatch/core/` | **核心逻辑**，纯 Java，零 Android 依赖 |
| `app/src/main/java/com/mctool/mcpatch/MainActivity.java` | 界面与文件选择 |
| `app/src/main/java/com/mctool/mcpatch/ApkFileProvider.java` | 把成品以 `content://` 交给安装器（免 androidx） |
| `tools/desktop/DesktopHarness.java` | 桌面验证夹具，用同一份核心代码在 PC 上跑 |
| `tools/desktop/VerifyProbe.java` | 桌面验证「源包签名检测」，对真实 APK 直接跑 |
| `tools/desktop/ExportKeyMaterial.java` | 把 keystore 导成运行时用的 PKCS#8 + X.509 两个文件 |
| `tools/build_manual.ps1` | 不依赖 Gradle/Android Studio 的手工构建脚本 |
| `tools/genkey.ps1` / `tools/genkey.sh` | **生成你自己的签名密钥**（构建前跑一次） |
| `app/src/main/assets/*.example` | 公用示例密钥（公开，开箱即用；真密钥不在此列） |
| `app/keystore/mc-patch.jks` | 仅 AGP 给**工具自身**签名用（构建期 JVM 行为） |
| `fixtures/` | 测试用皮肤图与资源包 |

> 安装工具本身：`adb install -r MCPatchTool-v1.0.apk`，或者手机点开装。
> 它和《我的世界》是不同包名，互不影响。

---

## 1. 怎么用

1. **选源 APK**：点「选择《我的世界》APK」。选完会自动做一次**体检**（下面 1.1），
   当场告诉你这个包能不能直接覆盖安装。
2. **改名字**：勾上「修改玩家名称」，输入想要的字（比如 `Miku`）。右边有「清空」。
3. **换皮肤**：勾上「替换皮肤」→「从相册选皮肤图」选一张 64×64 或 128×128 的图，
   再选**细手臂（Alex）**或**粗手臂（Steve）**。
4. **换资源包**：勾上「替换资源包」，选一个或多个 `.zip` / `.mcpack`
   （**可多选叠加**，按加入顺序覆盖；右边「清空」可重来）。
5. **一键生成** → 完成后点「立即安装」。

至少勾一项；进度条和下面的日志会实时告诉你卡在哪一步。
生成过程中「一键生成」按钮会变成「取消」。

**所有选择都会被记住**（名字、手臂、勾选项、上次用的源包/皮肤/资源包列表、自动另存开关、
外观选择），下次打开直接点「一键生成」就行。

底部按钮：

| 按钮 | 作用 |
|---|---|
| **立即安装** | 调起系统安装器（首次会要「安装未知应用」权限） |
| **复制日志** | 把设备信息 + 内置指纹 + 源包/资源包信息 + 完整日志复制到剪贴板，报问题时直接粘给我 |

产物默认还会**自动另存一份到公共 Download 目录**（「一键生成」下面那个勾选框控制，默认打开），
所以想要一个能在文件管理器里找到的副本时不用额外操作。

### 1.1 外观：默认跟随系统，右上角可手动切

标题栏右上角有个太阳/月亮按钮，点一下在三种模式间循环：

| 图标 | 模式 | 行为 |
|---|---|---|
| 半日半月 | **跟随系统**（默认） | 系统切深色，本页跟着切 |
| 太阳 | 浅色 | 强制浅色 |
| 月亮 | 深色 | 强制深色 |

选择会记住。生成过程中切换不会打断任务，会提示「下次打开生效」。

实现上没有引 androidx 的 AppCompat，而是用 `values/` 与 `values-night/` 两份
`Theme.MCPatch`（父主题分别是 `Theme.Material.Light.DarkActionBar` 与 `Theme.Material`），
手动指定时在 `setContentView` 之前 `setTheme()` 覆盖系统值。

### 1.2 导入存档（和改包无关，**不需要 root**）

界面最下面第 5 节，跟上面改包的四节完全独立，**不用选 APK**：

1. 「选择 .mcworld / .zip 存档」挑一个世界存档；
2. 点「导入到游戏」。

工具会把文件复制到自己的共享目录，再用 `content://` + 显式 Intent 交给《我的世界》，
**由游戏自己调用它的 `LevelArchiver::_importWorld` 写进存档目录**。

| 要点 | 说明 |
|---|---|
| 为什么不用 root | 写存档目录的是**游戏自己**，它当然能写自己的 `Android/data`；工具只负责把文件递过去 |
| 会动我现有的世界吗 | **不会**。导入是*新建*一个世界，不碰已有的 |
| 为什么建议先退出游戏 | ~~游戏开着时走 `onNewIntent`；退出后走 `onCreate`，两条路游戏都实现了，但退出状态下更稳~~ **实测反了，见下** |

> **导入的正确顺序：先把游戏打开到「离线模式」世界列表，按 Home 键，再回来点导入。**
>
> 实测（真机）：**游戏没在运行时冷启动导入**，出现的症状是
> **全程竖屏 + 列表里没有这个世界 + 保存退出时闪退**。原因：
> - 清单里 `MainActivity` 写死 `android:screenOrientation=1`（**竖屏**），
>   游戏是靠运行时调 `AppPlatform_android::changeOrientation()` 才翻成横屏的
>   —— 竖屏说明**正常初始化没跑**；
> - `.so` 里的导入是**排队**的：`GameArguments::_tryImport_RequestPermission`
>   → `LevelLoader::queueLevelForImport` → `checkForPendingLevelImport`
>   （在下一次**加载关卡**时处理）→ `pushImportExportProgressScreen`
>   → `AppPlatform::copyImportFileToTempFolder` → `LevelArchiver::importLevel`。
>   也就是说"导入"和"打开这个世界"是同一条流程，游戏是**被导入流程直接带进世界的**，
>   从未经过列表安装那一步 —— 所以进得去、列表里却没有。
>
> 游戏已经运行（停在世界列表）时发 Intent，走的是 `onNewIntent`，游戏状态完整，
> 方向与列表都正常。
| 扩展名 | 已经是 `.mcworld/.mcpack/.mctemplate/.mcaddon` 就原样用；是 `.zip` 会**解开看内容**：有 `level.dat` 当世界（`.mcworld`），有 `manifest.json` 当资源包（`.mcpack`） |
| **嵌套自动展平** | 游戏是把文件**原样解压**到自己新建的世界目录里的（`minecraftWorlds/<新ID>/<zip 里的内容>`），所以 `level.dat` 必须在 zip 根目录。zip 里多套了一层就会变成 `<新ID>/<子目录>/level.dat`，游戏完全读不到 —— 工具会**自动剥掉那层前缀**再交给游戏，顺带丢掉 `__MACOSX/` 之类的垃圾 |
| 找不到游戏 | 会在 `com.netease.mc.qihoo` / `com.netease.mc.aligames` / `com.netease.mc` / `com.mojang.minecraftpe` 里依次找 |

> **存档版本要求**：客户端是 2017-12 的构建，**比客户端新的存档会被游戏拒绝加载**
> （提示"更新版本的该游戏保存了这一等级，因此无法加载"）。
> 请用**同期或更早**的世界存档。详见第 8 节。

> **导出没有做**，这是查过之后的结论，不是偷懒 —— 原因见第 8 节。

### 1.3 源包体检（选完包就告诉你结果）

选完 APK 之后，工具会在后台做三件事，并把结果直接显示在源包那一栏：

```
包名 com.netease.mc.qihoo    版本 0.2.0.25445
大小 157.3 MB
签名：与内置密钥一致 ✅ 可直接覆盖安装
结构：网易版 ✅ 皮肤定义 + 2 个语言文件
```

| 检查项 | 怎么判断 | 不一致时 |
|---|---|---|
| **签名** | 用 apksig 解析源包真实签名，取出证书 SHA-256，与内置密钥指纹**动态比对** | 警告「装之前必须先卸载原版」 |
| **结构** | 查 `skindefs.json` 与 `texts/*.lang` 在不在（正是本工具要改的文件） | 警告缺了哪一项，说明对应功能会失效 |

> 这个签名判断以前是**写死的**「和 v19 一样」，所以选官方原版也会误报「可直接覆盖安装」。
> 现在改成动态读，实测能正确区分（见 4. 已验证的事实）。
>
> 体检会顺带把源包拷到本地工作目录 —— 生成时本来就要拷，所以不算白干，
> 而且这样能在你点生成**之前**就发现问题，不用等拷完 165 MB 才报错。

---

## 2. 它到底改了 APK 里的什么

所有路径都是从你的 v19 包里实际拆出来确认过的，不是猜的。

### 2.1 玩家名称

```
assets/resource_packs/vanilla/texts/zh_CN.lang
assets/resource_packs/vanilla/texts/en_US.lang
```

把这三行的值换成你输入的名字：

```
skin.name.alex=...
skin.name.steve=...
skin.name.dummy=...
```

> **为什么是这里**：这个网易版本是把「皮肤显示名」当本地玩家名用的，
> 你的 v19 就是把 `skin.name.alex=艾莉克斯` 改成 `skin.name.alex=Miku`，
> 进游戏名字就变成 Miku 了。
>
> 三个键一起改，是为了不依赖游戏到底读哪个槽位。
> 原文件是 **UTF-8 带 BOM、LF 换行、末尾无换行**，改写时全部原样保留；
> 大量行带 `\t#` 尾巴（zh_CN 里 4805/5183 行都有），
> 这几行按 v19 的做法把尾巴去掉（v19 去掉后实测生效）。

### 2.2 皮肤 + 手臂粗细

```
assets/resource_packs/skins/skinpacks/Base/alex.png
assets/resource_packs/skins/skinpacks/Base/alex_dev.png
assets/resource_packs/skins/skinpacks/Base/steve.png
assets/resource_packs/skins/skinpacks/Base/steve_dev.png
assets/resource_packs/skins/skinpacks/Base/skindefs.json
```

* 四张 PNG **原包都是 64×64**。v19 只换了 `alex.png` / `alex_dev.png` 就生效了；
  这里把 `steve*` 一起换掉，免得将来默认槽位一变就失效。
* `dummy.png` 是 `type: Custom`（玩家自己导入皮肤的占位槽），**故意不动**。

手臂粗细改的是 `skindefs.json` 里每个皮肤的 `geometry`：

| 选项 | geometry | 体型 |
|---|---|---|
| 细手臂（Alex） | `geometry.humanoid.customSlim` | 3 像素宽的手臂 |
| 粗手臂（Steve） | `geometry.humanoid.custom` | 4 像素宽的手臂 |

这两个几何体在同目录 `base.json` 里定义（它的顶层键就是
`geometry.humanoid` / `geometry.humanoid.custom` / `geometry.humanoid.customSlim`）。
Alex 和 Steve 两条记录会一起改成所选体型，只有 `dummy` 保持原样。

### 2.3 资源包

把资源包整棵树**覆盖进**：

```
assets/resource_packs/vanilla/...
```

**为什么不是注册成独立资源包**：这个 APK 里**根本没有**资源包注册表
——没有 `valid_known_packs.json`、没有 `resource_packs.json`、没有 `options.txt`
（全包 3991 项按字节扫过）。基岩版的全局资源包是运行时记在数据目录里的，
改 APK 没法登记新包。而 `vanilla` 永远处于激活状态，
覆盖它等价于「这个包一直挂在最上层」，这也正是基岩版本身的覆盖语义。

三个例外：

| 例外 | 原因 |
|---|---|
| 包自己的 `manifest.json` / `pack_icon.png` 不覆盖 | 那是包元数据，盖掉 vanilla 的会让游戏认不出内置包 |
| `texts/*.lang` 用**追加合并** | 免得包只带半份语言文件时把游戏 UI 文案整片弄丢；基岩版 lang 是后出现的键覆盖先出现的，所以追加天然让资源包的翻译优先 |
| 外层套了一层文件夹的包会自动剥掉前缀 | 兼容 `MyPack/manifest.json` 这种打包方式 |

**多选叠加**：选了多个包时按加入顺序依次应用 ——
同名文件后面的覆盖前面的，语言文件按顺序依次追加（所以最后一个包的翻译优先）。
实测两个包同时有 `textures/blocks/stone.png` 时，最终生效的是后加入那个（见 4. 已验证的事实）。

---

## 3. 关键设计决策

### 3.1 绝不重编译资源

`resources.arsc` / `AndroidManifest.xml` / `res/` / `lib/*.so` **逐字节原样搬运**。
你的 v19 说明里踩过这个坑（apktool 重编译 manifest 后「联网时皮肤变 Steve」），
所以这里连 apktool 都不装，只做 zip 层面的文件替换。

实测结果：`resources.arsc`、`AndroidManifest.xml`、`classes.dex`、
`lib/armeabi-v7a/libminecraftpe.so`、`assets/web/index.html` 与原包**逐字节相同**。
`classes.dex` 完全不动 —— v19 的 smali 补丁（XML 弹窗、全屏、悬浮球）原样保留。

### 3.2 手写 ZIP 写入器

`java.util.zip.ZipOutputStream` 做不到这三件事，所以 `RawZipWriter` 是自己写的：

1. **未压缩条目的 4 字节对齐**（zipalign 等价）：靠往 local header 里塞
   padding extra field（id `0xD935`，和 zipalign 一致）。实测 3291 个 STORED 条目全部对齐，
   `zipalign -c -v 4` 校验通过。
2. **STORED 条目原样搬运**：直接沿用源包的 CRC 与长度，一个字节都不重新压。
3. **DEFLATE 条目流式写入**：用 bit3 + data descriptor，常驻内存与包大小无关
   （165 MB 的包在手机上也不会 OOM）。源 APK 自己给 `classes.dex` 用的就是这个写法。

### 3.3 用 Google 官方的 apksig 签名

`com.android.tools.build:apksig`（apksigner 的内核，**零依赖纯 Java**）。
自己拼 PKCS#7 或 v2 分块摘要很容易写错，而写错的表现是「装不上」不是「报错」，
很难 debug。

实测签名结果：**v2 + v3 校验通过**（`apksigner verify` 输出 true）。
v1 未启用是因为 minSdk 是 26（Android 8+），这个区间只认 v2/v3，v1 属于多余；
`apksig` 在 v2/v3 通过后会短路跳过 v1 校验，所以 `Verified using v1 scheme: false` 是正常现象。

### 3.4 签名：不用 KeyStore，直接吃 PKCS#8 + X.509

> **踩过的坑（真机实测）**：最初这里用的是 `KeyStore.getInstance("JKS")` 加载内置密钥库。
> 在 PC 上、在 Robolectric 里全部正常，**一装到手机就在签名阶段抛
> `java.security.KeyStoreException: JKS not found`**。
>
> 原因是：**Android 没有 JKS 实现**。它支持的 KeyStore 类型只有
> `BKS` / `BKS-V1` / `PKCS12` / `AndroidKeyStore`，而 JKS 是 JDK 专有格式。
> 这一类「宿主 JVM 有、Android 没有」的偏差最难查，因为桌面全绿。

现在改成直接读两个文件，解析只用
`KeyFactory.getInstance("RSA")` 与 `CertificateFactory.getInstance("X.509")`
—— 这两个 provider 在 Android 和 JVM 上都一定存在，从设计上消除了环境差异：

| 文件 | 内容 | 进仓库吗 |
|---|---|---|
| `assets/mc-patch-key.pk8` | PKCS#8 未加密 DER 私钥（实际使用的那把） | ❌ `.gitignore` 排除 |
| `assets/mc-patch-cert.pem` | X.509 证书，PEM | ❌ 排除 |
| `assets/mc-patch-key.pk8.example` + `mc-patch-cert.pem.example` | **公用示例密钥**（指纹 `4AE02588…3D14`） | ✅ 故意公开 |

两者由 `tools/desktop/ExportKeyMaterial.java` 从 keystore 导出，
而 [`tools/genkey.ps1`](tools/genkey.ps1) / [`tools/genkey.sh`](tools/genkey.sh)
把"生成密钥 → 导成这两个文件"串成了一条命令。
`app/keystore/mc-patch.jks` 是**另一回事** —— 那是 **AGP 给工具自身签名**用的构建期材料。

### 3.5 签名密钥：**两把，别搞混**

| | 用途 | 跑在哪 | 仓库里有吗 |
|---|---|---|---|
| `app/keystore/mc-patch.jks` | **工具 APK 本身**的签名 | 构建期，桌面 JVM（JKS 没问题） | ❌ 不放，否则别人能签"更新版"覆盖安装 |
| `assets/mc-patch-key.pk8` + `.pem` | **改出来的游戏包**的签名 | 运行期，Android | ❌ 不放（自己 `genkey` 生成） |
| `assets/*.example` | 上面那对的**公用示例** | 运行期 | ✅ 放，开箱即用 |

**签名材料刻意不走 KeyStore**：Android 没有 JKS 实现，
`KeyStore.getInstance("JKS")` 在真机上直接抛 `KeyStoreException: JKS not found`，
而桌面 JVM / Robolectric 上却是好的 —— 这类"宿主 JVM 与 Android 密码学不一致"的偏差，
必须从设计上消除，而不是靠加测试。所以只依赖
`KeyFactory("RSA")` 与 `CertificateFactory("X.509")`。

**界面上必须处理三种合法状态**（同一份代码、不同构建）：

| 状态 | 界面行为 |
|---|---|
| `assets/` 里没有密钥（刚 clone 还没 `genkey`） | 红字提示"**请先跑 `tools/genkey.ps1` 生成**，再重新构建"，不会静默失败 |
| 用的是 `*.example` 公用示例密钥 | 明确告警："这是公开的示例密钥，谁都能签出能覆盖安装到你手机上的包" |
| 用自己的密钥 | 动态比对：与源包同签名 → "可直接覆盖安装"；否则 → "装之前需要先卸载原版" |

> 这三条以前只有第三条，而且测试把指纹**写死**成 `1E08A903…` ——
> 结果换个密钥构建测试就红。那是测试的错：**"能不能覆盖安装"本来就该是动态算的**。

**⚠️ 换密钥的代价**：一旦用某个密钥装过改包，以后就必须一直用同一个，
否则系统拒绝覆盖安装 → 只能卸载重装 → **`Android/data/` 被删，存档全没**。
所以先想清楚再动手，并且把这两个文件另外备份一份。

界面上会显示当前证书指纹以及能不能覆盖安装；生成前还会先自检一次签名材料，
免得白拷一个 165 MB 的包最后才失败。

### 3.6 核心与界面彻底分离

`core/` 里 7 个类**没有任何 `android.*` import**。好处是同一份代码能在 PC 的 JVM 上
跑完整流程 —— 于是「生成出来的 APK 对不对」这件事可以在电脑上先验证干净，
而不用靠手机试。`tools/desktop/DesktopHarness.java` 就是干这个的。

### 3.7 为什么签名检测用 apksig 的 ApkVerifier，而不是系统的 PackageManager

要知道"选中的源包能不能覆盖安装"，就得读出它的签名证书。两条路：

| 方案 | 问题 |
|---|---|
| `PackageManager.getPackageArchiveInfo(path, GET_SIGNATURES)` | 受 Android 11+ 的**包可见性**规则影响，可能直接返回 null；而且它是 Android API，只能在真机上试，PC 验证不了 |
| **`com.android.apksig.ApkVerifier`（本工具选的）** | 自己解析归档，不受包可见性影响；顺带告诉你签名是否真的校验通过；**纯 Java，能放进 core 在 PC 上验证** |

只查 v2/v3（`setMinCheckedPlatformVersion(28)` / `setMaxCheckedPlatformVersion(34)`），
跳过最慢的 v1 JAR 全量摘要 —— 实测 157 MB 的包约 **250 ms**（PC），手机上估计 1~3 秒，
放在后台体检里完全可接受。

这个判断放在纯 Java 的 `core/ApkSignerHelper.inspectSigner()` 里，
所以可以用 `tools/desktop/VerifyProbe.java` 在电脑上直接对着真实 APK 验证：

```powershell
javac -cp tools\lib\apksig-8.7.3.jar -d build\probe `
      app\src\main\java\com\mctool\mcpatch\core\*.java tools\desktop\VerifyProbe.java
java -cp "build\probe;tools\lib\apksig-8.7.3.jar" VerifyProbe <某个.apk>
```

---

## 4. 已验证的事实

用你真实的 v19 包（164,912,583 B）在 PC 上端到端跑过，产物经
`apksigner` / `aapt2` / `zipalign` / Python 逐项比对：

| 检查项 | 结果 |
|---|---|
| 签名（apksigner 独立验签） | v2 ✅ v3 ✅，证书 = v19 同指纹（可覆盖安装） |
| `aapt2 dump badging` | 正常读出包名 `com.netease.mc.qihoo`、versionCode `840025445`、targetSdk `22` |
| `zipalign -c -v 4` | `Verification succesful` |
| 条目数 | 3991 → 3991（丢 3 个旧签名，补 3 个新签名） |
| `resources.arsc` | 逐字节相同 ✅ |
| `AndroidManifest.xml` | 逐字节相同 ✅ |
| `classes.dex` | 逐字节相同 ✅（v19 的 smali 补丁完好） |
| `lib/armeabi-v7a/libminecraftpe.so` | 逐字节相同 ✅ |
| 四张皮肤 PNG | 全部替换为用户图（128×128 也正常） |
| `skindefs.json` | Alex/Steve 的 geometry 按选择切换，`customSlim` 无残留 |
| 两个 `.lang` | BOM 保留、`skin.name.*` 三行改写、资源包语言行合并成功 |
| 资源包覆盖 | 同名文件覆盖成功；`vanilla/manifest.json`、`pack_icon.png` 未被污染 |
| 外层套文件夹的资源包 | 自动识别 `MyPack/` 前缀，未产生多余目录 |
| 二次修改 | 把成品再当源改一次：皮肤/几何/名字全部正确更新，第一遍注入的资源包完好保留 |
| 4 字节对齐 | 3291 个 STORED 条目，0 个未对齐 |
| **Android 框架级测试** | Robolectric **3/3 通过**：Activity 真的被创建起来、布局能膨胀、22 个控件 id 全部绑定成功、内置密钥被识别为 v19 那把、勾选联动正确 |
| **apksig 在 Android 上能否跑** | `jdeps` 列出 apksig 依赖的 **23 个 JDK 包在 android.jar(API 34) 中全部存在**（含 `javax.security.auth.x500`、`java.time`）；Gradle/D8 clean 重建**零缺类警告** |
| **release 包是否被测试依赖污染** | 否：dex 中不含 `Landroidx/`（Robolectric 只是 `testImplementation`） |
| **真机实跑（Android 手机）** | 界面正常、源包拷贝/校验/改名/换皮肤/重打包全部跑通；并借此发现签名阶段真机上会抛 `JKS not found`（见 3.4，已修） |
| **源包签名动态检测**（用随包发布的 core 代码实测） | v19 改包 → `1E08A903…`，判定**一致**（261 ms）；**官方原版 APK** → `A40DA80A…`（网易签名），判定**不一致**（155 ms）；工具自身 208 KB 包 → 4 ms。**这正是修掉的那个误报**：改之前选官方原版也会显示"可直接覆盖安装" |
| **单元测试** | Robolectric **9/9 通过**（5 个界面/记忆/主题 + 4 个导入存档相关） |
| **存档导入的 content URI**（Robolectric 实测） | 交给游戏的那个 `content://com.mctool.mcpatch.files/import/MyWorld.mcworld` 能被 `ContentResolver` 正常打开、内容逐字节一致、MIME 为 `application/octet-stream`；文件名与扩展名完整保留（游戏靠它判类型） |
| **存档导入的越权防护** | 白名单之外的目录、`%2F` 编码的路径穿越、段数不对的 URI 全部被拒绝 |
| **世界包嵌套展平**（真机踩坑的精确复现） | `+OYCABpnCQA=/level.dat` 这种多套一层、外加 `__MACOSX/` 垃圾和根目录说明文件的世界包：能正确识别出世界根前缀、展平后 `level.dat` 落在根目录、垃圾被丢掉、条目数正确、数据逐项保留 |
| **扩展名嗅探** | 含 `level.dat` 的 `.zip` → `.mcworld`；含 `manifest.json` 的 `.zip` → `.mcpack`；已是对得上的扩展名则不动；看不懂的内容兜底按世界处理且不崩 |
| **资源包叠加语义**（桌面实测） | 两个包都含 `textures/blocks/stone.png` 时，最终是**后加入那个包**的图；后加入包独有的 `gold.png` 正常新增；两份 `texts/zh_CN.lang` 按包顺序追加（pack2 的行在后 → 运行时优先）；BOM 保留；`vanilla/manifest.json` 与 `pack_icon.png` 未被污染 |
| **外观（深色模式）** | `values/` + `values-night/` 两份主题；右上角按钮的菜单项与图标在 Robolectric 里断言通过 |

耗时：165 MB 的包一次生成约 **1.7 秒**（PC，SSD；手机实测约 1.4 秒跑到签名那一步）。

---

## 5. 怎么构建

### 方式 A：Android Studio（推荐）

直接 `File → Open` 打开本目录。首次同步会自动拉 AGP 与 apksig。
如果 `local.properties` 里的 `sdk.dir` 指向本仓库自带的 SDK，Studio 会提示改成你自己的。

命令行等价操作：

```bash
./gradlew assembleRelease
# 产物: app/build/outputs/apk/release/app-release.apk
```

### 方式 B：不装 Android Studio / 不装 Gradle

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_manual.ps1
# 产物: manual-build\MCPatchTool.apk
```

这条路径用 `aapt2 compile/link` + `javac` + `d8` + `zipalign` + `apksigner`
一步步手工完成，只依赖 `tools/` 下的 JDK 与 build-tools。

> 产物刻意放在 `manual-build\` 而不是 `build\`：后者是 Gradle 的地盘，
> `gradlew clean` 会把手工构建的结果一起删掉。

> 本仓库的 `tools/android-sdk` 是我为验证方便临时**直下 zip** 拼出来的，
> 其中 `platforms/android-34/package.xml` 与 `source.properties` 被手工改过：
> 官方 `platform-34-ext12_r01.zip` 声明的是 `platforms;android-34-ext12` 且
> `AndroidVersion.IsBaseSdk=false`，而 AGP 8.5 找的是 `platforms;android-34`，
> 不改会报 `Failed to find Platform SDK with path: platforms;android-34`。
> 你自己用 Android Studio / `sdkmanager "platforms;android-34"` 装的话不会有这个问题，
> 那两个文件会被官方版本覆盖。

---

## 5.5 怎么在 PC 上验证核心逻辑（不用手机）

因为 `core/` 是纯 Java，可以直接在电脑上跑完整流程，产物再用 `apksigner` 独立验签：

```powershell
$T   = "路径\mc-tool"
$JDK = (Get-ChildItem "$T\tools\jdk" -Directory | Select-Object -First 1).FullName
$CP  = "$T\tools\lib\apksig-8.7.3.jar"

# 1) 编译核心 + 夹具（注意：不编译 MainActivity，它依赖 android.jar）
$srcs  = Get-ChildItem "$T\app\src\main\java\com\mctool\mcpatch\core" -Filter *.java |
         ForEach-Object { $_.FullName }
$srcs += "$T\tools\desktop\DesktopHarness.java"
& "$JDK\bin\javac.exe" -encoding UTF-8 -cp $CP -d "$T\build\desktop-classes" @srcs

# 2) 跑一遍：源包 输出包 签名材料所在目录 名字 皮肤图 slim|classic 资源包
& "$JDK\bin\java.exe" -cp "$T\build\desktop-classes;$CP" DesktopHarness `
    "Minecraft-0.2.0.25445-offline-v19.apk" "$T\out\demo.apk" `
    "$T\app\src\main\assets" "Miku" "$T\fixtures\test_skin_64.png" slim "-"

# 3) 独立验签
& "$T\tools\android-sdk\build-tools\34.0.0\apksigner.bat" verify --print-certs "$T\out\demo.apk"
```

`-` 表示「这一项不改」。那个目录里要有 `mc-patch-key.pk8` 与 `mc-patch-cert.pem`。
第 3 步应该看到 `Verified using v1/v2/v3 scheme: true`，并且证书 SHA-256 是
`1e08a903…5953`（与 v19 一致）。

---

## 5.6 框架级单元测试（Robolectric）

```bash
./gradlew testReleaseUnitTest
# 报告: app/build/reports/tests/testReleaseUnitTest/index.html
```

`app/src/test/java/com/mctool/mcpatch/MainActivityLaunchTest.java` 会在 JVM 上跑
**真实的 Android 框架代码**，把 `MainActivity` 真的创建起来，覆盖
「装上去一打开就崩」这类最致命的问题：

| 用例 | 验的是什么 |
|---|---|
| `activityInflatesAndEveryIdResolves` | 主题能解析、布局能膨胀、**27 个 `findViewById` 的 id 全部存在**（id 对不上就是启动 NPE） |
| `signerMaterialHandlesAllThreeStates` | 签名材料的三种状态（还没生成 / 用公开示例 / 用自己的）都被正确处理，且提示可操作 |
| `checkboxesDriveEnabledState` | 勾选框联动（勾上才启用输入框/预览）、选文件按钮始终可用、默认选中细手臂、自动另存默认打开、生成可用而安装初始禁用 |
| `choicesSurviveRestart` | **选择记忆**：重建 Activity 后名字、手臂、各勾选项、自动另存开关都能恢复 |
| `themeToggleMenuIsWired` | **外观切换按钮**：菜单项存在、图标能解析（太阳/月亮/跟随三张图都在包里） |

另一个测试类 `SaveImportTest`（4 个用例）覆盖存档导入里**可以在本地验证**的部分：
交给游戏的 `content://` URI 能否正常打开、内容是否逐字节一致、文件名/扩展名是否保留、
越权与路径穿越是否被挡住，以及 `.zip` 的扩展名嗅探（世界 vs 资源包）。
**真正"游戏有没有接住这个 Intent"只能真机验证** —— 这一点没法在这里测。

> **这套测试的能力边界要说清楚**：Robolectric 跑在**宿主 JVM** 上，用的是 JVM 的
> 密码学实现，不是 Android 的 Conscrypt。所以它**证明不了**「Android 上某个
> provider 一定存在」—— 这一轮真机上报的 `JKS not found` 就是个活例子：
> 当时 `KeyStore.getInstance("JKS")` 在 Robolectric 里全绿，装到手机才炸。
> 修法不是加测试，而是**从设计上不依赖任何可能缺失的 provider**（见 3.4）。
> 另外它**不覆盖** SAF 选文件、后台线程、调起安装器这三块 —— 那需要真机。

如果你在一台**Java 无法在用户主目录建文件**的受限环境里跑（比如某些沙箱），
Robolectric 会因为建不出 `<user.home>/.robolectric-download-lock` 而失败，这时可以：

```bash
./gradlew testReleaseUnitTest -Dmc.robolectric.home=/可写目录/.robohome
```

---

## 6. 已知限制

1. **只能改离线可见的东西**。玩家名走的是皮肤显示名，联机大厅/账号相关的名字由服务端下发，
   工具改不到（而且这个包的在线后端 2017 年就下线了）。
2. **资源包是覆盖进 vanilla 的**，不会在游戏「资源包」列表里出现为独立包，
   也不能单独关掉。想要可开关的多资源包，得走运行时数据目录，不是改 APK 能做的。
3. **皮肤必须是 64×64 或 128×128**，其它尺寸会被拒绝并提示。工具会把图片重新编码成
   PNG（强制 ARGB_8888，保留透明度）。
4. **换皮肤时四张 PNG 会被写成同一张图**。如果游戏将来改了默认槽位指向 `dummy.png`，
   需要再调整（目前 `dummy.png` 按原样保留）。
5. **minSdk 26**（Android 8.0+）。这个下限是 apksig 带来的：`jdeps` 显示它用到
   `java.time`（API 26 起才有，不开 desugaring 就用不了）。
   想让工具支持更老的机器，把 `app/build.gradle` 的 `minSdk` 降到 24 并打开
   core library desugaring 通常可行 —— 注意它并不依赖 `java.nio.file`，
   所以不用为了这一点把 minSdk 顶到 26。
6. **想用自己的签名密钥**：仓库里只有一把**公开的示例密钥**，一条命令就能换成自己的：

   ```powershell
   # Windows
   powershell -ExecutionPolicy Bypass -File tools\genkey.ps1
   ```
   ```bash
   # Linux / macOS
   ./tools/genkey.sh
   ```

   它做三件事：`keytool` 生成 RSA 2048 自签证书 → 用
   `tools/desktop/ExportKeyMaterial.java` 导成
   `mc-patch-key.pk8` + `mc-patch-cert.pem` → 写进 `app/src/main/assets/`。
   然后**重新构建**工具 APK 即可。（手动做法也行，见
   `app/src/main/assets/README.md`；注意 `-dname` 里的**逗号是字段分隔符**，
   字段值里不能再出现逗号，这里踩过。）

   ⚠️ **换密钥的代价**：一旦用某个密钥装过改包，以后就必须一直用同一个，
   否则系统拒绝覆盖安装 → 只能卸载重装 → **`Android/data/` 被删，存档全没**。

7. 想直接用公开的示例密钥（图省事，但谁都能签出能覆盖安装到你手机上的包）：

   ```powershell
   powershell -ExecutionPolicy Bypass -File tools\genkey.ps1 -UseExampleKey
   ```
   （卸载会连带删掉 `Android/data/<包名>/`，而存档正好在那里 —— 见第 8 节）。
7. **源 APK 会被完整拷贝一份到工作目录**（`Android/data/com.mctool.mcpatch/files/work/input.apk`），
   加上产物一共需要大约 **2 倍源包大小 + 80 MB** 的空闲空间，空间不足会提前报错。
8. **没有在真机上跑过 UI**。环境里没有连接 Android 设备，也开不了模拟器
   （WHPX 未启用，开启需要重启；软件模拟跑 165 MB 的补丁包不现实）。
   已经做掉的验证：核心逻辑桌面端到端跑通并独立验签、Activity 用 Robolectric
   真跑起来、apksig 依赖的 JDK 包逐个核对过 android.jar。
   **还没被覆盖的只剩三块**：SAF 选文件、后台线程的进度回传、调起系统安装器。
   这三块都是标准写法，但需要你实机点一次确认。

---

## 7. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 「这个 APK 里找不到 …skindefs.json」 | 选的不是网易版《我的世界》的包，或者已经被别的工具拆坏过 |
| 「皮肤必须是 64x64 或 128x128」 | 用图片编辑器裁成这两种尺寸之一再导入 |
| 128×128 皮肤进游戏看着不对 | 原包四张皮肤都是 64×64。基岩版对自定义皮肤支持 128×128，但内置进皮肤包的纹理按 64×64 布局更保险；遇到渲染异常就把图缩成 64×64 再导一次 |
| 资源包报「没有 manifest.json」 | 不是有效的基岩版资源包（`.mcpack` 本质是 zip，里面必须有 `manifest.json`） |
| 点「立即安装」跳到设置页 | Android 8+ 需要先允许本应用「安装未知来源应用」，授权后回来再点一次 |
| 安装时提示签名冲突 | 说明源包不是用改包那把密钥签的，得先卸载原版再装。**注意卸载会删掉 `Android/data/<包名>/`，而存档正好在那里** —— 见第 8 节 |
| 生成很慢 | 主要耗时是把源 APK 从 SAF 拷到本地。第二次生成同一份 APK 会复用缓存，快很多 |
| 界面顶部红字「没有找到签名密钥」 | `assets/` 下没有 `mc-patch-key.pk8` / `mc-patch-cert.pem`。公开仓库刻意不带私钥，跑一次 `tools/genkey.ps1`（或 `tools/genkey.sh`）生成即可；没有它没法给产出包签名 |
| 早期版本报 `java.security.KeyStoreException: JKS not found` | 已修：那是用 `KeyStore.getInstance("JKS")` 导致的，Android 没有 JKS 实现。换成 PKCS#8 + X.509 后不再依赖任何 KeyStore provider（见 3.4）。**请用本轮重新构建的 APK** |

---

## 8. 附录：网易版存档到底存在哪（以及为什么导不出来）

这是从 v19 包里查出来的确定结论，不是猜的。

**Java 层**（`com/mojang/minecraftpe/MainActivity.smali`）：

```smali
.method public getExternalStoragePath()Ljava/lang/String;
    const/4 v0, 0x0
    invoke-virtual {p0, v0}, Lcom/mojang/minecraftpe/MainActivity;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    invoke-virtual {v0}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;
    return-object v0
.end method
```

也就是返回 **`/sdcard/Android/data/com.netease.mc.qihoo/files`**，不是公共存储。

**native 层**（`libminecraftpe.so` 里的路径常量）：

```
/games/com.netease/
/games/com.netease/minecraftWorlds
/games/com.netease/minecraftStructures/
/games/com.netease/resource_packs
/games/com.netease/behavior_packs
External File Level Storage      ← 基岩版的外置文件存档后端
level.dat / levelname.txt / db/  ← 标准基岩版世界结构
```

两者拼起来，**世界存档在**：

```
/sdcard/Android/data/com.netease.mc.qihoo/files/games/com.netease/minecraftWorlds/<世界ID>/
```

**所以"导不出来"是真的**：Android 11 起，`/sdcard/Android/data/<包名>/` 对
文件管理器、对「所有文件访问」权限、对 SAF 全部封闭，只有该系统 App 自己和 root 能进。
不是这游戏故意锁的，是系统的分区存储规则。

### 想导入/导出存档，可行路径有三条

| 方案 | 可行性 | 说明 |
|---|---|---|
| **走游戏自己的导入通道**（← 本工具采用的） | ✅ **导入可行，全设备通用** | 游戏实现了 `LevelArchiver::_importWorld`，且 `MainActivity.processIntent()` 会处理 `ACTION_VIEW + content://`。工具把 `.mcworld` 递过去即可，**零特权、零门槛** |
| Root / Shizuku | ✅ 可行 | 直接读写那个目录。导出**只能**走这条（或下面第三条） |
| 改 `getExternalStoragePath()` 指向公共目录 | ⚠️ 半可行 | 一处 smali 就能让存档变公开，但 **Android 11+ 上应用无法用 File API 在 `/sdcard/games/` 建目录**（分区存储限制），除非再让游戏拿到「所有文件访问」权限；而且老存档在游戏里会"消失"。没做 |

**导出为什么不做**（这是查证后的结论，不是取舍）：

1. 存档在 `Android/data` 里，普通应用硬读不到（系统级限制，只有 root/Shizuku 能进）；
2. 游戏自带的「导出世界」按钮在移动端被 `$pocket_edition` 藏起来了，但**把按钮显示出来也没用** ——
   C++ 的导出流程必须经过 `AppPlatform::pickFile`，而
   ```
   _ZN19AppPlatform_android9pickImageER20ImagePickingCallback   ← Android 实现了选图片
   _ZN19AppPlatform_android8pickFileE                          ← 压根不存在
   ```
   **Android 端根本没有实现 `pickFile`**。这正是 Mojang 在移动端隐藏这套 UI 的原因。

所以结论是：**导入能免 root 做到，导出不能。** 工具只做了导入。

### 8.1 世界包的结构要求（实测踩过）

游戏收到文件后是把它**原样解压**到自己新建的世界目录里的：

```
minecraftWorlds/<游戏生成的ID>/<zip 里的内容>
```

所以 **`level.dat` 必须在 zip 根目录**。实测踩到的坑：一个多套了一层文件夹的 zip，
导入后目录成了 `minecraftWorlds/qPIFAOQgAkkA=/+OYCABpnCQA=/level.dat`，
游戏完全读不到（进度条走完，世界列表里什么都没有）。

工具现在会**自动展平**：找到最浅的 `level.dat`，剥掉它的父目录前缀重打一份，
顺带丢掉 `__MACOSX/` 这类垃圾和世界根之外的说明文件。

### 8.2 存档版本必须不高于客户端

这是**系统的硬性要求**，不是网易的限制：

- 这个客户端是 **2017-12-12** 的构建（native 里那条 OBT 路径 `obt20171212182501` 就是构建时间戳）；
- 用 2018-02-15 的世界导入后，列表能认出来，但启动时报
  **"更新版本的该游戏保存了这一等级，因此无法加载。"**
- 这是基岩版自己的版本校验（`level.dat` 里的 `StorageVersion` /
  `lastOpenedWithVersion`）。**版本比客户端新的世界一律加载不了。**

**所以请用同期或更早的世界存档**（2017-12 及以前）。基岩版对更旧的存档是向后兼容的，
会就地升级，所以"更旧"没问题，"更新"才是死路。

> 能不能把 `level.dat` 里的版本字段改小来绕过？
> 理论上可以，但**区块数据（`db/`）的存储格式是跟着版本走的** ——
> 光改版本号可能变成"能进世界但方块错乱"，甚至崩。所以工具目前**不做**这件事。

### 8.3 客户端版本与 StorageVersion 是怎么查出来的

给这个构建做适配，得先知道它的两个"能力值"。

**① 客户端版本 = `[1, 1, 3, 50]`**

**最可靠的来源是客户端自己写的世界**：让游戏新建一个世界，那个 `level.dat` 里的
`lastOpenedWithVersion` 就是 `GameVersion::current()` 的输出（字段语义就是"最后打开它的版本"，
每次保存都会覆写）。实测客户端自建世界写的是 `[1, 1, 3, 50]`。

> ⚠️ **踩过的坑**：一开始我在 `.so` 里搜到明文 `1.2.0.4`，就当成了游戏版本 —— **错的**。
> 那段字符串周围全是 libcurl 的东西（`bind` / `resolved to` / `content unencoding`），
> 是某个**库**的版本号。同一个文件里还有 `7.54.1`（libcurl）、`1.2.8`（zlib）、
> `1.1.0`（OpenSSL）—— 全是库版本。
> **教训：`.so` 里的版本串不能随便认，得看它周围的上下文。**

**② 客户端 StorageVersion = 5** —— 这是个全局变量，藏在 ELF 的**动态符号表**里。
`.so` 虽然是 stripped 的，但 `.dynsym` 还在：

```
_ZN15SharedConstants21CurrentStorageVersionE   .dynsym, size=4, value=0x1be67e4
   → 用段头把地址映射回文件偏移，读 4 字节小端 = 5
```

这个值**和客户端自建世界写进去的 `StorageVersion` 完全一致**，两边互相验证 ✔

校验逻辑因此很明确：`GameVersion(世界的 lastOpenedWithVersion)` 与
`GameVersion::current()` 比较（`_ZNK11GameVersionltERKS_`），世界更新就拒绝，
报 `disconnectionScreen.futureVersion`。

> 附：`tools/elf_version.py` 读 ELF 动态符号表，`tools/nbt_dump.py` 是基岩版 NBT 解析器
> （8 字节头 + 小端），`tools/make_compat_world2.py` 做版本降级。

### 8.4 实测：Logic Gates（1.2.10.1 的地图）

| 字段 | Logic Gates | 客户端 1.1.3.50 | 后果 |
|---|---|---|---|
| `lastOpenedWithVersion` | `[1,2,10,1]` | `[1,1,3,50]` | **就是那个 `futureVersion` 报错** |
| `StorageVersion` | `6` | `5` | LevelDB 区块格式的档位 |
| `NetworkVersion` | `200` | `113` | 可能还有一道网络版本校验 |

另外键的数量也不同（地图 68 个 / 客户端 50 个）—— 地图多出来的是
`hasLockedBehaviorPack`、`isFromLockedTemplate` 这类更新版本才有的字段。
正常情况下未知标签会被忽略，不是阻塞点。

`level.dat` 是「8 字节头 + **明文** NBT」，而且这几个字段都是定长的，
所以**直接原地改字节**就行，不用重新序列化整个 NBT ——
实测变体 A2 只改了 **3 个字节**，B2 改 4 个，C2 改 5 个，其余逐字节一致、长度不变。

三个变体的用途是**分级定位**：只改声明 → 再降格式档位 → 再降网络版本。
都是副本，原存档不动。

### 8.5 网易版 H5 启动器架构（理解一切的关键）

**你在游戏里看到的世界列表不是基岩版的界面，是一个网页。** 网易把 H5 启动器盖在基岩版引擎上面：

```
┌─────────────────────────────────────────────┐
│  H5 启动器（WebView）  ← 你看到的"离线模式"列表  │
│    assets/web/index.html + 12 个 JS bundle   │
│    static/img/empty03_*.png ← 空列表那张插画   │
└───────────────┬─────────────────────────────┘
                │ window.mc.sendMessage("json:" + {...})
                │ ← window.ComPyCallback.resolve(json, tag)
┌───────────────▼─────────────────────────────┐
│  内嵌 Python 模块（ComPy = Communication+Py）  │
│    setting / h5adaptor / resource_management │
├─────────────────────────────────────────────┤
│  基岩版引擎（libminecraftpe.so）              │
│    LevelArchiver::_importWorld / LocalWorldList│
└─────────────────────────────────────────────┘
```

**为什么"导入的世界不显示"**：H5 列表读的是**网易自己的「世界记录」**，不是扫目录：

```js
get_sorted_world_records      // 列表的唯一数据来源
add_world_record({item_id, name, icon, version, second_type, path})
```

世界只有两条路能进入记录：
1. `create_world_ctrl_h5` —— 在游戏里「创建世界」
2. `download → decompress_map → add_world_record` —— 从网易商店下载地图

**H5 里没有任何本地文件导入入口**（12 个 bundle 里搜 `type="file"` / `FileReader` /
"选择文件" / "导入" 全部为 0）。所以基岩版自己的 `_importWorld` 把世界装进
`minecraftWorlds/` 之后，网易的列表**永远不会去看那个目录** —— 两条路根本不交汇。
手动拷贝、重启游戏都没用，与版本无关。

**桥接 API 全貌**（从 JS 里抽出来的函数名）：
- 世界/记录：`get_sorted_world_records` / `get_world_record` / `add_world_record` /
  `remove_world_record` / `copy_world` / `init_world_item_id_mapping` /
  `get_local_image_by_item_id` / `get_item_version_info` / `play_world` /
  `play_world_by_item_id` / `create_world_ctrl_h5` / `get_level_summary` /
  `get_world_setting` / `set_world_setting`
- 资源包/皮肤：`get_resource_pack_records` / `add_resource_pack_record` /
  `get_addon_records` / `add_addon_record` / `add_skin_record` / …
- 路径：**只有** `get_minecraftWorlds_path` / `get_resource_packs_path` /
  `get_raw_skins_path`
- 解压：`h5adaptor.decompress_map(压缩包, 目标目录, true)`

> **关键限制**：桥接里**没有任何列目录 / 选文件 / 读写文件的接口**。
> 所以"改 JS 让列表扫目录"这条路在纯 JS 层面**不可能**。
> 但反过来，"用 `decompress_map` + `add_world_record` 走网易自己的官方流程导入"
> 是**可行且不需要 root** 的 —— 因为没有列目录需求，喂一个约定路径即可。

**通道是全局的，所以注入很轻**（`index.html` 末尾本来就有 v19 补丁的内联脚本）：

```js
window.mc.sendMessage("json:" + JSON.stringify({
    module_name, func_name, use_instance, args, tag,
    return_callback:    "ComPyCallback.resolve",
    exception_callback: "ComPyCallback.reject"
}));
// 回复：window.ComPyCallback.resolve(json, tag)
```

**为什么改 H5 能长期有效**：`resource_management` / `h5adaptor` 这些模块
**在整个 APK 里都搜不到**（不在 `.so`、不在 DEX、没有任何 `.py`/`.pyc`），
说明是运行时从服务器下发的（`ReqH5VersionStage` / `updateH5Version` /
`setH5ServerUrl`）。而网易的 CDN 早已 404（正是当初 `<Code>NoSuchKey</Code>` 的根源），
**下载不到更新版本 → APK 里 `assets/web/` 那份会长期生效**。
v19 补丁改 `index.html` 能生效，也印证了本地副本确实被使用。

### 8.6 借壳法（已实测成功）

既然列表读记录、记录指向一个**目录名**，那就可以：

1. 在游戏里点「创建世界」建一个空世界（这样它会被登记进记录）；
2. 用 root 把该世界目录的**内容**换成目标地图（**目录名绝对不许改**，记录是按目录名对上的）；
3. 回列表点「启动」→ 走的是正常流程，H5 会正确退下、方向正常、不闪退。

**实测：成功。** 这验证了整个模型。缺点是需要 root、且一次只能换一个世界。

**为什么"通过导入 Intent 进世界"会出现竖屏 + 列表没有 + 退出闪退**：
导入是排队的（`LevelLoader::queueLevelForImport` → `checkForPendingLevelImport`
在**加载关卡**时处理），游戏是被导入流程**直接带进世界**的，跳过了 H5 的正常流程；
而 H5 那层没退下去，就表现为"能听见音效但看到的是竖屏列表"。

> 顺带一个必须知道的风险：卸载 App 时系统会一并删掉 `Android/data/<包名>/`，
> 而存档正好在那里。所以"先卸载原版才能装上改包"这个操作<b>会删存档</b>，
> 除非你已经在 root 下把它拷走。这一点没法用普通方式规避。

> 注意：工具本身是另一个包名的 App，**没有 root 的情况下连它自己也读不到**
> `com.netease.mc.qihoo` 的 `Android/data` 目录 —— 这一点在设计功能前必须先说清楚。
>
> **顺带一个必须知道的风险**：卸载 App 时系统会一并删掉 `Android/data/<包名>/`，
> 而存档正好在那里。所以"先卸载原版才能装上改包"这个操作<b>会删存档</b>，
> 除非你已经在 root 下把它拷走。这一点没法用普通方式规避。

---

## 9. 导入外部世界（不用 root）

这是本项目最有意思的一部分 —— 结论是：**在网易版里导入外部存档，可以做到不需要 root。**

### 9.1 为什么"把世界拷进目录"永远不生效

网易版的世界列表**不是基岩版的界面，是一个网页**（`assets/web/` 里的 H5 启动器，
游戏启动时会把它解压到数据目录的 `web/` 再加载）。这个网页读的是**网易自己的「世界记录」**：

```
<数据目录>/games/com.netease/storge/stream/resource_management/world_records/<level_id>.json
```

**一个世界一个 JSON，文件名就是世界目录名。** 列表不是扫目录出来的，
所以基岩版自己的导入器（`LevelArchiver::_importWorld`）把世界装进 `minecraftWorlds/` 之后，
网易的列表**永远不会去看那个目录** —— 手动拷贝、重启游戏都没用，与版本无关。

更麻烦的是：**记录对应的世界目录不存在时**，那个 Python 模块读不到 `level.dat`，
会抛 `'NoneType' object has no attribute 'get'`，导致**整条列表读取崩溃（白屏）**；
而且它崩溃后会把**整个 `world_records/` 目录删掉**重置自己。

### 9.2 怎么绕过去：用网易自己的写文件接口

H5 能调的原生接口里，`h5adaptor.decompress_map(源zip, 目标目录, true)` 的
**目标目录是任意的** —— 于是把「世界记录 JSON」也打成一个 zip，
就能直接解压进记录目录。**全程不需要 root**，因为写文件的是游戏自己。

还有两个必须尊重的特性：

| 特性 | 后果 | 本工具的对策 |
|---|---|---|
| **会把包内目录结构完全压平** | `db/000014.ldb` 解出来会丢 `db/` 前缀 → 世界没有区块 | **按顶层目录分组**：每个组一个包，解压时目标目录直接指向那个子目录（`db.zip → <世界>/db`） |
| **成功后会消耗掉源 zip** | 同一个包只能用一次 | 正好当"已导入"标记：下次点击自动落到下一个槽位，**不需要任何状态记录** |

### 9.3 使用流程

```
工具（本 App）
  ① 选 .mcworld → ② 体检（版本/StorageVersion/NetworkVersion）
  ③ 需要时自动降级 → ④ 拆成几个包写进公共 Download/
        mcweb_1_root.zip / mcweb_1_db.zip / … / mcweb_1_record.zip
游戏（用本工具生成的改包）
  ⑤ 点左下角「导入世界」→ 游戏自己把世界和记录写进去
  ⑥ 完全退出游戏再重新打开 → 世界出现在列表里，点启动正常进入
```

**工具会往改包的 `assets/web/index.html` 里注入导入界面**（`assets/mc-import.js`），
所以必须用本工具生成的 APK 才能导入。注入是幂等的，且**只改这一个文件**，
`resources.arsc` / `AndroidManifest.xml` / `classes.dex` / `lib/*.so` 全部逐字节原样。

### 9.4 客户端能力值（降级的目标值）

| 字段 | 客户端（网易 0.2.0.25445） | 怎么读出来的 |
|---|---|---|
| `lastOpenedWithVersion` | `[1, 1, 3, 50]` | 客户端自建世界的 `level.dat` |
| `StorageVersion` | `5` | `.so` 的 ELF `.dynsym` 里 `SharedConstants::CurrentStorageVersion`（并与自建世界互验） |
| `NetworkVersion` | `113` | 客户端自建世界的 `level.dat` |

世界比这些值新的话，游戏会报 **"更新版本的该游戏保存了这一等级，因此无法加载"**。
降级只改 `level.dat` 里那 3 个定长字段（实测**只差 5 个字节**），长度不变、其余字节一个不碰。

> ⚠️ `StorageVersion` 是**磁盘格式档位**，改小它属于"骗"客户端。
> 实测 Logic Gates（`1.2.10.1` / StorageVersion 6）降级到 `1.1.3.50` / 5 之后
> **能加载、能游玩、游戏还会往它的 LevelDB 里写新数据**，但这不保证对所有存档都成立。

### 9.5 限制

- **必须用本工具生成的改包**（导入界面在里面）；
- 导入后**必须重启游戏**（记录是启动时读进内存缓存的）；
- 一次导入占一个槽位，共 **9 个**，循环复用（第 10 次会覆盖第 1 次导入的世界）；
- 槽位 ID 固定是 `mcw<1..9>`，所以**已导入的世界不要再手动改名目录**。

---

## 10. 源码结构

```
app/src/main/java/com/mctool/mcpatch/
├── MainActivity.java            界面 / 文件选择 / 源包体检 / 选择记忆 / 存档导入 / 后台线程
├── ShareFileProvider.java       极简 ContentProvider：把生成的 APK 交给安装器、
│                                把 .mcworld 交给游戏（免 androidx 的 FileProvider）
└── core/                        ← 纯 Java，无 android.* 依赖，可桌面运行
    ├── PatchSpec.java           参数 + 校验
    ├── PatchLog.java            进度回调
    ├── ApkPatcher.java          主流程：替换 / 资源包合并 / 重打包
    ├── RawZipWriter.java        手写 ZIP writer（4 字节对齐 / 原样搬运 / 流式 deflate）
    ├── LangPatcher.java         .lang 改写（BOM / LF / \t# 尾巴）
    ├── SkindefsPatcher.java     skindefs.json 手臂几何切换
    └── ApkSignerHelper.java     apksig 签名（PKCS#8+X.509）+ ApkVerifier 读源包签名
```
