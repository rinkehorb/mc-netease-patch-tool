# 我的世界（网易版）改包与存档导入工具

针对 **网易版《我的世界》Android**（包名 `com.netease.mc.qihoo`，验证于 `0.2.0.25445`）的一套工具。
纯 Java 实现，**改包和导入存档都不需要 root**。

> ⚠️ 与网易、Mojang、Microsoft 没有任何关系，是个人学习与自用工具。
> 请勿分发修改后的游戏 APK。改包与导入外部存档可能违反游戏用户协议，**风险自负**。

---

## 它能做什么

### 1. 一键改包

选一个**本地的**游戏 APK 文件，改完之后直接在手机上生成**已签名的可安装 APK**：

| 改动 | 实际改的是什么 |
|---|---|
| **玩家名称** | `assets/resource_packs/vanilla/texts/{zh_CN,en_US}.lang` 里的 `skin.name.alex/steve/dummy`（这个版本就是拿"皮肤显示名"当本地玩家名用的） |
| **皮肤 + 手臂粗细** | `assets/resource_packs/skins/skinpacks/Base/` 下的 `alex.png` 等，以及 `skindefs.json` 里 `geometry.humanoid.customSlim`（细/Alex）与 `geometry.humanoid.custom`（粗/Steve） |
| **资源包叠加** | 把包的内容覆盖进 `assets/resource_packs/vanilla/`（`texts/*.lang` 走追加合并，包自己的 `manifest.json`/`pack_icon.png` 不覆盖）；**支持多个包按顺序叠加** |
| **导入界面** | 往 `assets/web/index.html` 注入一个「导入世界」按钮，见下面第 2 点 |

**绝不重编译 `resources.arsc` / `AndroidManifest.xml`** —— 那是改包最容易改坏的地方
（资源 ID 会乱）。这两个文件连同 `classes.dex`、`libminecraftpe.so` 全部**逐字节原样搬运**。

### 2. 导入外部世界（**不需要 root**）

这是这个项目最有意思的部分。网易版的世界列表**不是基岩版的界面，而是一个网页**（H5 启动器），
它读的是网易自己的「世界记录」而不是扫目录 —— 所以把 `.mcworld` 拷进存档目录
**永远不会显示**，手动拷贝、重启游戏都没用，与版本无关。

这里走通了网易 H5 自己的写文件通道（`h5adaptor.decompress_map` 的**目标目录是任意的**），
把「世界记录 JSON」也打成一个包解压进去，于是：

```
工具：选 .mcworld → 体检版本 → 需要时自动降级 → 拆包写进 Download/
      （登记成图片 .png —— 见下面「打包成 .png」那条，这一步很反直觉但必须）
游戏：点「导入世界」→ 重启游戏 → 世界出现在列表，点启动正常进入
```

原理、踩过的坑、客户端能力值都在 [`mc-tool/README.md`](mc-tool/README.md) 第 9 节和
[`mc-re/probe/实测发现.md`](mc-re/probe/实测发现.md)。

---

## 别人怎么用（完整流程）

### 0. 先搞清楚三件事

1. 工具**不动游戏本身**，它是在**你本地的 APK 文件**上做修改，产出新文件。
2. **你必须自己准备一份原版 APK 文件**。工具没法从"已安装的应用"里提取它
   （Android 11+ 不允许应用读别人的 APK）。
3. 工具产出的包**与官方同签名**，可以直接**覆盖安装** —— 不用卸载、不丢存档 ✔
   只有在你换了签名密钥、或系统提示签名不一致时才需要卸载，
   而**卸载会连 `Android/data/` 一起删掉，你的存档就全没了** ✗。

### 1. ⚠️ 备份你的世界（**最重要的一步，别跳**）

⚠️ **这版游戏没有「导出世界」菜单**（齿轮只打开「世界设置」，实测确认）✗，
备份只能走下面两条路（都不需要 root ✔）：

* **Shizuku + MT管理器**（推荐）：用「无线调试」激活 Shizuku →
  MT管理器开 Shizuku 模式 → 进 `Android/data/com.netease.mc.qihoo/` 整个复制出来（约 10 MB）
* **电脑 adb**：先在手机上打包再拉 ——
  `adb shell "cd /sdcard/Android/data/com.netease.mc.qihoo/files/games && tar czf /sdcard/b.tgz com.netease"`
  然后 `adb pull /sdcard/b.tgz`（⚠️ 直接 pull 目录会静默失败，必须先 tar）

要备份的核心是 `.../files/games/com.netease/minecraftWorlds/`（世界本体）
和 `.../storge/stream/resource_management/world_records/`（世界记录，列表靠它）。

> 从备份还原时：把世界目录**打成 zip**，用工具第 5 步导入回去 ✔

> 血泪教训：卸载重装会**静默清空** `Android/data/com.netease.mc.qihoo/`，
> 包括 `games/com.netease/minecraftWorlds/` 和世界记录。这是真的丢过存档的地方。

### 2. 准备原版 APK

从官方渠道拿到网易版《我的世界》的 APK 文件，放到手机上。版本越接近 `0.2.0.25445` 越好
（导入功能的降级目标值是按这个版本读出来的，见 [`mc-tool/README.md`](mc-tool/README.md) 9.4）。

### 3.（可选）换成你自己的签名密钥

不改也能用（仓库里带了一把**公开的示例密钥**），但用自己的更稳妥，而且**一旦选定就别再换**：

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File mc-tool\tools\genkey.ps1
```
```bash
# Linux / macOS
./mc-tool/tools/genkey.sh
```

生成后需要**重新构建**工具 APK 才会生效。**普通用户直接用 Release 里打好的 APK 就可以**，
那把示例密钥够用（缺点只是"别人也能签出能覆盖安装到你手机上的包"）。

> **为什么"选定就别换"**：一旦你用密钥 A 装了改包，下次装密钥 B 的包时系统会拒绝覆盖安装，
> 你必须先卸载 → **存档没了**。

### 4. 装工具、改包

1. 装 `dist/MCPatchTool-v26.10.10-1010-1848.apk`（见 [dist/](dist/) 或 Releases）
2. 选源 APK → 勾「改名」/「换皮肤」/「加资源包」→ 一键生成
3. **直接覆盖安装**（同签名 ✔ 不用卸载 ✔ 不丢存档 ✔）
4. 安装刚生成的 APK，打开

> 生成界面里应该能看到提示：与你的改包同签名 → 可直接覆盖安装；
> 如果显示的是「示例密钥」告警，说明你用的是仓库里那把公开密钥。

### 5. 把世界导回来

1. 工具里选一个 `.mcworld` 存档 → **「准备导入」** → 它把几个包**登记成图片（`.png`）**
   写进 `Download/`
2. 打开游戏 → 点左下角 **「导入世界」** → 看到"导入完成"
3. **完全退出游戏，再重新打开**（世界记录是启动时读进内存的）
4. 世界出现在列表里，点「启动」进去

### 6. 以后

- 再改名字/皮肤：重复第 4 步的 2~4。**同一个密钥**，这次可以直接覆盖安装，**不用卸载、不丢存档**。
- 再导入世界：重复第 5 步。共 9 个槽位轮换。

---

## 常见问题

**Q：要 root 吗？**
不用。改包、导入世界、导出世界都不需要。只有"手动去修世界记录文件"才需要。

**Q：改完的包能联机吗？**
基本不能。签名变了，网易的登录/联机校验过不去。这个工具主要面向**离线单人**。

**Q：导入后列表白屏？**
说明有"孤儿记录"（记录指向的世界目录不存在）—— 这是那个 Python 模块的坑，
成因和修法写在 [`mc-tool/README.md`](mc-tool/README.md) 9.1 节。

**Q：导入的世界没有地形/区块？**
`db/` 没进去。本工具的拆包逻辑已经处理了（**按顶层目录分组**，因为那个接口会把目录压平），
手工操作才会踩到 —— 见 9.2 节。

**Q：导入时报 `[Errno 13] Permission denied`？**
你用的是**旧版工具**。Android 11+ 有一条反直觉的规则：**别的 App 创建的非媒体文件
（`.zip` / `.json` / `.txt`）任何位置、任何权限都读不到** —— 实测过 `Download/`、
`Android/media/<包名>/` 全都 EACCES，而且那个游戏 `READ_EXTERNAL_STORAGE` 已授予、
`targetSdk` 才 22，**根本不是权限问题**。

解法是**把包伪装成媒体文件**：用 MediaStore 登记成图片（后缀 `.png`、MIME `image/png`），
媒体文件是允许别按路径读的。文件内容仍是标准 zip，`decompress_map` 不看后缀。
1.0 之后的版本已经这么做了。完整分析见 [`mc-tool/README.md`](mc-tool/README.md) 9.3.1 节。

**Q：那 `Android/media/<包名>/` 到底行不行？**
**分系统版本**：Android 13 上实测可以，Android 15 上不行。所以最终方案是 `.png` 那条路。

**Q：游戏更新了还能用吗？**
改包是按版本做的，新版本请重新走一遍流程。注意新版本的 `lastOpenedWithVersion` /
`StorageVersion` 等能力值可能变了，导入功能的降级目标值需要相应更新（9.4 节有怎么读出来）。

---

## 仓库结构

```
mc-tool/          工具本体（Android App + 纯 Java 核心）
  app/src/main/java/com/mctool/mcpatch/
      core/           纯 Java 核心，无 android.* 依赖，可在桌面 JVM 上跑同一份代码
        ApkPatcher          改包主流程（绝不重编译资源表）
        RawZipWriter        手写 zip（对齐 STORED 条目、流式 DEFLATE）
        ApkSignerHelper     用 Google apksig 签名 + 源包签名体检
        LevelDat            level.dat 的版本字段读写（原地改字节）
        WorldImportPrep     世界体检/降级/按顶层目录拆包
      MainActivity.java     界面
      ShareWriter           把包登记成图片写进 Download（跨 App 可读的关键）
  app/src/main/assets/mc-import.js   注入到游戏 H5 的导入界面
  app/src/main/assets/README.md      ★ 签名密钥怎么来（第一次构建前先看这个）
  tools/genkey.ps1 / genkey.sh       ★ 生成你自己的签名密钥
  tools/desktop/    桌面验证夹具（用同一份核心代码在 PC 上跑）
mc-re/            针对这个客户端的逆向与补丁过程记录（文档 + 自写脚本）
  probe/          真机探针与实测记录
dist/             成品 APK
```

## 构建

需要 **JDK 17** + **Android SDK（build-tools 34）**。

```bash
# 第一次：先生成签名密钥（否则工具能编译但没法给产出签名）
powershell -ExecutionPolicy Bypass -File tools\genkey.ps1    # 或 ./tools/genkey.sh
```

**方式 A：Gradle**（推荐，会自己下依赖）

```bash
gradle build        # 产物在 app/build/outputs/apk/
gradle test         # 单元测试（含 Robolectric 框架级测试）
```

**方式 B：不装 Gradle**（只需要 JDK + build-tools）

```powershell
powershell -File mc-tool\tools\build_manual.ps1
```

> 发布版 APK 还需要 `mc-tool/app/keystore/mc-patch.jks` —— 那是**工具自己的签名身份**，
> 刻意没放进仓库。照 [`mc-tool/app/keystore/README.md`](mc-tool/app/keystore/README.md) 自己生成一个，
> 或者改成 debug 签名。

## 签名密钥：有两把，别搞混（**务必读一下**）

| | 用在哪 | 在仓库里吗 |
|---|---|---|
| `app/keystore/mc-patch.jks` | **工具 APK 自己**的签名（构建期，桌面 JVM） | ❌ 不放（否则别人能签"更新版"覆盖安装） |
| `assets/mc-patch-key.pk8` + `mc-patch-cert.pem` | **改出来的游戏包**的签名（运行期，纯 PKCS#8 + X.509） | ❌ 不放（`.gitignore` 排除） |
| `assets/*.example` | 上面那对的**公用示例密钥** | ✅ 放（故意公开，方便开箱即用） |

**为什么运行期不用 KeyStore**：Android 没有 JKS 实现，
`KeyStore.getInstance("JKS")` 在真机上直接抛 `KeyStoreException: JKS not found`，
而桌面 JVM 上却是好的 —— 这类"宿主 JVM 与 Android 密码学不一致"的坑必须从设计上绕开，
所以只依赖 `KeyFactory("RSA")` 与 `CertificateFactory("X.509")`。

**换密钥的代价**：一旦用某个密钥装过改包，以后就必须一直用同一个，否则只能卸载重装
（**会丢存档**）。先想清楚，再动手，并且把密钥文件另外备份一份。

## 许可

MIT，见 [LICENSE](LICENSE)。`mc-tool/tools/lib/apksig-8.7.3.jar` 是 Google 的作品，Apache-2.0。
---

## ⚠️ 关于本仓库内置的签名密钥

本仓库**包含**用于给改包签名的密钥（mc-tool/app/src/main/assets/mc-patch-*.pk8/pem
与 mc-tool/app/keystore/mc-patch.jks）。

这把密钥**直接取自网易《我的世界》的安装包**，属**公开性质** ——
任何人解包游戏 APK 都能提取出来，**它不是只有作者知道的秘密**。
把它留在仓库里，是为了让别人 clone 下来就能构建出**能覆盖安装的包**。

> ⚠️ **仅供个人自用。** 不要用它签任何要公开发布的东西；
> 想换成自己的密钥：跑 mc-tool/tools/genkey.ps1，并在 .gitignore 里取消相应注释。
