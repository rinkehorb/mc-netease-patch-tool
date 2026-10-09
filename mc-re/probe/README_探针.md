# MCPROBE —— 网易版 H5 启动器只读探针

## 这是什么

一个**只读**探针，用来把网易版《我的世界》里 **H5 界面 ↔ Python 模块**之间的 JSON 桥看清楚。

### 为什么要做它

网易把 H5 启动器（网页）盖在基岩版引擎上面。"离线模式"世界列表**不是基岩版的界面**，
而是 `assets/web/` 里的一堆 HTML/JS。列表的数据来源是网易自己的「世界记录」，
**不是扫目录** —— 所以基岩版自己导入的世界永远不会显示。

要让外部 `.mcworld` 进入列表，唯一不需要 root 的办法是：**用网易自己的官方流程**：

```js
worlds.Path = await 桥接("setting",             false, "get_minecraftWorlds_path")
await               桥接("h5adaptor",           false, "decompress_map", [zip, dest, true])
await               桥接("resource_management", true,  "add_world_record", [{...}])
```

但 `add_world_record` 的参数（`item_id` / `icon` / `version` / `second_type` / `path`）
和 `tag` 的确切格式都还不知道。**探针就是去把这几个未知量问出来。**

## 它做了什么

| 行为 | 说明 |
|---|---|
| 钩住 `window.mc.sendMessage` | 记录 H5 **发出去**的每个桥接请求（模块名、函数名、args、tag） |
| 钩住 `window.ComPyCallback.resolve/reject` | 记录**回来**的每个回复（原始 JSON） |
| 主动调用两个只读接口 | `setting.get_minecraftWorlds_path`、`resource_management.get_sorted_world_records` |
| 屏幕底部浮层显示 | `MCPROBE` 面板，可复制、可清空、可收到 24px 一条 |

**只读。不调用任何写接口，不碰存档，不改 H5 自身逻辑。**

## 怎么用

1. **覆盖安装** `Minecraft-0.2.0.25445-probe.apk`
   （与 v19 同一把签名钥匙、同一 versionCode → 不用卸载、不丢存档）
2. 打开游戏，把「无法连接至服务器…是否以离线模式启动？」那个弹窗过掉，进入**世界列表**
3. 屏幕底部会悬浮一个 **MCPROBE** 面板（会挡住下半屏，点「收起」能缩成一条）
4. 点「复制」，把内容发回来；或者**直接截图**（面板字够清楚）

## 要看什么

| 面板上的行 | 含义 |
|---|---|
| 顶栏 `send=true cb=true` | 两个钩子都装上了（这是最重要的前提） |
| `[BOOT]` | UA、`window.mc` / `ComPyCallback` 是否存在 |
| `[OUT]` | H5 自己发出的请求 —— **注意看 `tag=` 的真实格式** |
| `[IN#…]` | 回复的原始 JSON —— **世界记录的完整字段在这里** |
| `[OK·world_records]` | `get_sorted_world_records` 的返回，**这就是 3a 的字段模板** |
| `[FAIL·…]` | 失败原因。`3 秒内没收到回复` = 我用的 tag 没被接住，得改成 H5 的格式 |
| 面板**完全没出现** | 说明 H5 不是从 `assets/web/index.html` 加载的（这也是重要结论） |

## 它是怎么被装进去的

`50_build_probe.py` 沿用老项目那套「整包重写」策略：

- 只替换 `assets/web/index.html` 一个条目（31775 → 42923 字节，末尾注入探针脚本）
- 其余 **3990 个条目按原始压缩方式、原始时间戳原样复制**，逐字节不变
- 丢掉旧的 `META-INF/`，未压缩条目做 4 字节对齐（zipalign 等价）
- 用 `tools/debug.keystore` 签名（证书 `1E:08:A9:03…59:53`，与 v19 同款）

自检结果：`testzip OK`、无缺失/多余条目、除目标外**无内容差异**、
`resources.arsc` / `AndroidManifest.xml` / `classes.dex` / `libminecraftpe.so` **全部原样**、
3296 个未压缩条目**对齐 0 个失败**。

## 怎么退回

把 v19 原包覆盖安装回去即可（同一把钥匙）。存档不受影响。
