# MC 一键修改器（MCPatchTool）

给网易《我的世界》APK 换个名字 / 换皮肤 / 换手臂粗细 / 叠资源包 / 导入外部存档的小工具。
**不联网、不上传，全部在手机本地完成。**

> 📚 **想看完整来龙去脉（853 行的历史版本）**：`../调试记录/README-mc-tool-历史完整版.md`
> 本 README 只保留"必要部分"：怎么用、改了 APK 的什么、为什么这么设计、怎么构建与验证。

---

## 0. 交付物清单（`../成品/`）

| 文件 | 是什么 |
|---|---|
| `MCPatchTool-v26.10.10-1010-1848.apk` | **本工具**（约 0.3 MB，不是游戏） |
| `Minecraft-…-v20a-4px.apk` | 底包 A：默认 **Steve + 粗手臂 4px** |
| `Minecraft-…-v20b-3px.apk` | 底包 B：默认 **Alex + 细手臂 3px** |
| `Minecraft-…-offline-v19.apk` | **根底包**：能离线玩的原版改包（所有改包的出发点，务必另存一份） |
| `Minecraft-…-import.apk` | 老包（v19 + 导入界面 + Miku 皮肤），已被 v20a/v20b 取代 |

> 五个游戏包**同一把密钥签名** → 可互相覆盖安装，不用卸载、不丢存档。

---

## 1. 怎么用

### 三条路径

```
① 改名字 / 换皮肤 / 叠资源包
   选源 APK（v20a 或 v20b）→ 勾选要改的 → 一键生成 → 立即安装（可直接覆盖）

② 换手臂粗细（3px ↔ 4px）
   直接点「6. 换手臂粗细（推荐 · 不用卸载）」→ 打开游戏 → 完全关掉 → 重开

③ 导入外部世界（.mcworld）
   选世界 → 准备导入 → 进游戏点左下角「导入世界」→ 完全退出游戏再重开
```

### 1.1 源包体检

选完 APK 会立刻报：包名/版本/大小、**签名是否与内置密钥一致**（决定能否覆盖安装）、
**结构是否网易版**（有没有 `skindefs.json` 与 `texts/*.lang`）—— 早发现比生成完才失败好。

### 1.2 外观

默认跟随系统深浅色，标题栏右上角可手动切（跟随系统 / 浅色 / 深色）。

### 1.3 关于手臂粗细为什么"有时不生效"

工具里第 3 节的「细/粗手臂」单选，只在**卸载游戏后重新安装**时才生效；
覆盖安装只换贴图、不改粗细（原因见 2.2）。**想随时换粗细用第 6 节** ✔

---

## 2. 它到底改了 APK 里的什么

只动这几类文件，**`classes.dex` / `resources.arsc` / `AndroidManifest.xml` / `lib/*.so`
全部逐字节原样搬运** —— 这就是离线能力不会丢的原因。

| 改动 | 文件 | 生效方式 |
|---|---|---|
| 玩家名称 | `resource_packs/vanilla/texts/*.lang` 的 `skin.name.*` | 覆盖安装即生效 |
| 皮肤贴图 | `resource_packs/skins/skinpacks/Base/{alex,alex_dev,steve,steve_dev}.png` | 覆盖安装即生效 |
| 手臂粗细 | `.../Base/skindefs.json` 的 `geometry` + **数组顺序** | **只在卸载重装后**生效（见 2.2） |
| 资源包 | 整棵树覆盖进 `resource_packs/vanilla/` | 覆盖安装即生效 |
| 导入界面 | `assets/web/index.html` 注入一段 JS | 覆盖安装即生效 |

### 2.1 玩家名称

网易版把「皮肤显示名」当本地玩家名用，所以改名字就是改 `texts/*.lang` 里的
`skin.name.alex/steve/dummy` 三行（保留 BOM，只改这三行）。

### 2.2 ★ 皮肤与手臂是**两套配置**（这条踩了很久）

| 改什么 | 存储位置 | 什么时候读 |
|---|---|---|
| **皮肤贴图** | APK 里的 `Base/*.png` | **每次启动都读** → 覆盖安装立刻生效 ✔ |
| **手臂体型** | 玩家档案：游戏私有目录的 `options.txt` | **只在首次运行时写一次** → 改 APK 不生效 ✗ |

* **默认皮肤 = `skindefs.json` 里 `skins` 数组的【第一条】**（用"把 Steve 挪到第一位"的
  全新安装实验证实 ✔）→ v20a / v20b 就是靠这个"锁"住默认外观的。
* **手臂体型的字段**：

  ```
  /data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe/options.txt
      game_skintypefull:Standard_Alex      → 细手臂 3px（实测 ✔）
      game_skintypefull:Standard_Steve     → 粗手臂 4px（实测 ✔）
  ```

  该目录 root 才能写，Shizuku 也只到 `Android/data` 那一层。

### 2.3 ★ 不 root 也能换手臂粗细（已做成工具功能）

关键：`options.txt` 在游戏**自己的私有目录**里 —— 普通应用碰不到，但**游戏自己能写**。
而游戏里的 H5 有一条 `h5adaptor.decompress_map(源zip, 目标目录, true)`，
以**游戏身份**解压写入，于是可以让游戏**自己覆盖自己的配置**：

```
工具：把改好的 options.txt 打成 zip，伪装成 .png 写进 /sdcard/Download/（mcarm_3px / mcarm_4px）
游戏：注入的 H5 脚本在启动时发现它 → decompress_map 写进 .../minecraftpe/
用户：完全关掉游戏 → 重开 → 手臂就是新的
```

**实测**：一加（有 root）先用 root 逐字节确认；**vivo（无 root）**走完整流程后
重启游戏手臂真的从 3px 变成 4px ✔

**三条必须注意的**：

* 源路径要用 `/sdcard/...` 这种写法 —— `/storage/emulated/0/...` 游戏读不到（`Errno 2`）。
* 源文件**必须叫 `.png`**（非媒体文件读不到 —— Android 11+ 的分区存储规则）。
* **不要在游戏运行时覆盖安装 APK** —— 安装会杀掉游戏，它会把**内存里的旧配置**存回去。
* ⚠️ **代价**：H5 没有读文本文件的接口，只能**整份覆盖** `options.txt` ——
  其他设置（画质 / 视野 / 语言…）会回到模板里的值（模板已把按钮尺寸设为 80）。

### 2.4 资源包

整棵树覆盖进 `resource_packs/vanilla/`（等价于一直挂最上层）。
**为什么不是注册成独立资源包**：这个 APK 里没有资源包注册表（没有 `valid_known_packs.json`、
没有 `options.txt`），基岩版的全局资源包是运行时记在数据目录的，改 APK 没法登记新包；
而 `vanilla` 永远处于激活状态，覆盖它正是基岩版本身的覆盖语义。选多个时按顺序叠加。

---

## 3. 关键设计决策

1. **绝不重编译资源** —— 只做"ZIP 级替换"，不碰 `resources.arsc` 与 `AndroidManifest.xml`，
   避免 aapt2 回编带来的连锁风险。
2. **手写 ZIP 写入器** —— 保持 STORED 条目的字节与对齐，产出包和源包结构一致。
3. **用 Google 官方 `apksig` 签名**（v1 + v2 + v3），核心是纯 Java、零依赖。
4. **不用 KeyStore** —— Android 上没有 JKS provider（真机踩过 `KeyStoreException: JKS not found`），
   所以直接用 PKCS#8 私钥 + X.509 证书构造签名器。
5. **两把密钥别搞混**：内置的 `mc-patch-key.pk8` 与 v19 同签名（可直接覆盖安装）；
   `*.example` 是公开的占位密钥，仅供别人自建。详见 `app/src/main/assets/README.md`。
6. **核心与界面彻底分离** —— `core/` 里是纯 Java，可以在 PC 上用夹具跑完整流程并独立验签。

---

## 4. 已验证的事实（要点）

* 核心逻辑在 PC 上端到端跑通并**独立验签**；Activity 用 Robolectric 起得来（本仓库 **25 个用例**）。
* **未 root 的 Android 15**（vivo）上：改名 / 换皮肤 / 加资源包 / 导入世界 / **免 root 换手臂**全部实测通过。
* **有 root 的 Android 13**（一加）上：`options.txt` 逐字节验证 + 内部目录全量快照对比。
* 产出的包与源包相比：`classes.dex` / `resources.arsc` / `AndroidManifest.xml` / `libminecraftpe.so`
  **逐字节相同**；签名指纹与内置密钥一致。

---

## 5. 怎么构建

### 方式 A：Gradle

```bash
./gradlew assembleRelease          # 产物: app/build/outputs/apk/release/app-release.apk
./gradlew testReleaseUnitTest      # 25 个 Robolectric 用例
```

### 方式 B：不装 Android Studio / 不装 Gradle（本仓库自带工具链）

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_manual.ps1
# 产物: manual-build\MCPatchTool.apk
```

### 5.1 在 PC 上验证核心逻辑（不用手机）

```bash
# 编译核心 + 桌面夹具（不编译 MainActivity，它依赖 android.jar）
javac -encoding UTF-8 -cp tools/lib/apksig-8.7.3.jar -d <classes> \
      app/src/main/java/com/mctool/mcpatch/core/*.java tools/desktop/DesktopHarness.java
# 跑一遍：源包 输出包 签名材料目录 名字 皮肤图 slim|classic 资源包 [导入脚本]
java -cp <classes>;tools/lib/apksig-8.7.3.jar DesktopHarness …
```

⚠️ **传 `skin=-` 时不会改写 `skindefs.json`**（做实验时很有用）；
⚠️ 源包**已经含 `__MCIMPORT__`** 时，注入会"先摘掉旧的再插新的"（所以源码更新的脚本能进得去）。

---

## 6. 已知限制（摘要）

* 只针对**网易《我的世界》**的结构，**不保证适用于网易《我的世界》的其他版本**。
* 换手臂粗细会**重置游戏设置**（原因见 2.3）。
* 工具**做不到自动备份存档**（普通应用读不到 `Android/data`，H5 也只有写没有读）——
  卸载前请务必自己备份，方法见 `../成品/使用说明.md` 第六节。
* 完整限制清单见历史完整版 README。

---

## 7. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 点「导入世界」全报 `Errno 13` | 用了旧版工具（包写成了 `.zip`）。Android 11+ 读不到别的 App 的非媒体文件，必须伪装成 `.png` |
| 点「导入世界」说"没有找到待导入的包" | 还没点「准备导入」，或上次的包已被游戏消耗（正常，重跑一次） |
| 导入后列表里没有 | 没重启游戏（世界记录只在启动时读一次） |
| 列表白屏 | 有"孤儿记录"（记录指向的世界目录不存在），见 9.1 |
| 手臂点完没反应 | 手机上装的改包是**旧版**（没有 H5 脚本）。用现在这个工具重新生成一个再装 |
| 改了粗细但进游戏没变 | `options.txt` 只在**启动时**读 —— 要**完全关掉游戏再打开** |

---

## 8. 附：网易版的几个关键事实

### 8.1 存档存在哪、为什么导不出来

存档在 `Android/data/com.netease.mc.qihoo/files/games/com.netease/`，
由 `minecraftWorlds/`（世界本体）+ `storge/stream/resource_management/world_records/`（世界记录）组成。
**普通应用读不到**（分区存储），而游戏本身**没有**「导出世界」菜单 ——
移动端的导出流程依赖 `AppPlatform::pickFile`，Android 端根本没实现，所以 Mojang 把入口藏了。
⇒ 导出只能靠 root / Shizuku / adb。

### 8.2 世界列表读的是"记录"，不是目录

网易版「离线模式」的列表来自**世界记录 JSON**，不是扫描 `minecraftWorlds/`。
所以把世界拷进去**永远看不见**，而且**记录指向的世界不存在会导致整个列表白屏**。

### 8.3 H5 启动器（理解一切的关键）

游戏主界面是 `assets/web/` 里的一套 WebView 应用，它通过
`window.mc.sendMessage("json:" + …)` 调用原生能力（模块/函数/参数/tag/回调）。
**完整接口表（63 组 module/func）见 `tools/H5桥接接口表.md`**，其中最有用的三条：

```
setting.get_minecraftWorlds_path / get_raw_skins_path     取路径
resource_management.*                                     世界记录、皮肤列表、资源包
h5adaptor.decompress_map(源zip, 目标目录, true)            以游戏身份解压写入（会压平目录、消耗源包）
```

> ⚠️ 压缩 JS 里 `!1` 是 `false`、`!0` 是 `true`；`use_instance` 传错会报
> `Can not find xxx in setting`（实测踩过）。

### 8.4 客户端能力值

`lastOpenedWithVersion=[1,1,3,50]`、`StorageVersion=5`、`NetworkVersion=113`
（从 `libminecraftpe.so` 的 `.dynsym` 读出来的）。世界包版本高于客户端时要降级。

---

## 9. 导入外部世界（不用 root）

**为什么"把世界拷进去"永远不生效**见 8.2。绕过去的办法：
世界记录也要写进去，而写文件只能靠**游戏自己** ——
就用 8.3 里的 `h5adaptor.decompress_map`（工具把世界拆成几个包放进共享目录，
游戏里点一下「导入世界」由 H5 写到位）。

* `decompress_map` 会**压平目录结构** → 所以按顶层目录分组，每组一个包，
  目标目录直接指向对应子目录（`db.zip` → `<世界>/db`）。
* 成功后会**消耗掉源 zip** → "已导入的槽位"天然消失，不需要任何状态记录。
* **包必须伪装成 `.png`** 才能被游戏按路径读到（Android 11+ 的分区存储规则，踩过三次）。
* 导入后必须**完全退出游戏再重开**（世界记录只在启动时读一次）。

---

## 10. 源码结构

```
app/src/main/java/com/mctool/mcpatch/
    MainActivity.java          界面（纯平台 API，零 androidx 运行时依赖）
    ShareWriter.java           把包伪装成 .png 写进 Download（MediaStore）
    ArmSwitch.java             手臂粗细：把 options.txt 打成包
    core/
        ApkPatcher.java        ZIP 级替换 + 重打包（含导入界面注入）
        LangPatcher.java       texts/*.lang 的 skin.name.*
        SkindefsPatcher.java   skindefs.json 的手臂几何切换
        PatchSpec.java         参数校验
        ApkSignerHelper.java   apksig 签名 / 验签
        RawZipWriter.java      手写 ZIP 写入器
tools/
    build_manual.ps1           手工构建（不依赖 Gradle）
    make_v20_bases.py          从 v19 + 官方母本生成 v20a / v20b
    set_custom_skin.sh         用 root 直接改 options.txt
    H5桥接接口表.md             63 组桥接接口 + 调用格式
    probe_*.js                 注入 H5 的探针（自动跑、结果打在屏幕上）
    desktop/DesktopHarness.java PC 上的端到端夹具
app/src/test/                  Robolectric 用例（25 个）
```

---

## 11. 更详细的记录在哪

| 想了解 | 去哪看 |
|---|---|
| 本 README 的完整历史版（853 行，含全部实验记录） | `../调试记录/README-mc-tool-历史完整版.md` |
| 桥接接口全表 + 探针怎么用 | `tools/H5桥接接口表.md` |
| 真机实测记录（世界记录格式、白屏成因、能力值） | `../mc-re/probe/实测发现.md` |
| root 调查（内部目录快照对比、options.txt 证据） | `../调试记录/root调查/` |
| 成品怎么用 / 出问题怎么办 | `../成品/使用说明.md` |
| 整个工作区地图 | `../工作区说明.md` |

---

## 12. 导入世界：踩坑与修复记录（2026-10-10）

这一轮把「免 root 导入外部世界」从要试好几次修到点一次就成，踩了 4 个真 bug + 5 个环境坑。
**完整记录见 ../调试记录/导入世界-踩坑与修复记录.md**，这里只列结论：

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | 弹「导入准备失败」但包其实已写好 ✗，再点一次就成 | 后台线程直接改 View ✗（CalledFromWrongThreadException）| 那两处包进 ui.post ✔ |
| 2 | Download 里堆一堆 mcweb_1_db (1).png …，游戏挑到坏的那份 → 「权限不足」| 删旧文件只按 DISPLAY_NAME = ? ✗， (N) 后缀删不掉 ✗ → MediaStore 自动改名 ✗ | 加 OR ... LIKE 'stem (%' + 新增 purgeSlot ✔ |
| 3 | 工具显示已准备好 ✗，游戏里**怎么点都导入不了** ✗ | 前面残留了半截槽位（只有 _db 没 _root）✗，H5 从槽位 1 依次扫 ✗ → 卡在那一格 ✗ → 后面的完整包轮不到 ✗ | **purgeAll**：每次「准备导入」先清掉所有 mcweb_* ✔（方案 A）|
| 4 | 点「导入世界」停在「开始检查槽位」 | 我用脚本改 JS 时把换行写成了**字面量** \n ✗ → 语法错误 ✗ | 用 chr(92)+chr(110) 定位替换 ✔ |

**另一个可选加固（方案 B，未做）**：H5 侧要求 
oot + db 都齐才算有效槽位 ✗，否则跳过 ✔。

**环境坑**（都不是产品问题，但每次浪费半小时 ✗）：
db push 直写 /sdcard/ 不落盘 ✗ / 忘了设 JAVA_HOME ✗ /
$env:W 撞 Gradle ✗ / $env:TEMP 指向工作区让 AGP 起不来 ✗ /
桌面夹具编译产物过期导致注入被跳过 ✗

