# 用 root 查"手臂体型存在哪" —— 操作步骤（照着做即可）

**目的**：找到 `/data/data/com.netease.mc.qihoo/` 里存着**手臂粗细（3px / 4px）**的那个文件。
找到之后，如果它能被直接编辑，就**不用卸载重装**也能换粗细 ✔ —— 那才是这个问题的真正解法。
（背景：手臂体型在首次运行时写死，之后改 APK 不生效，见 `mc-tool/README.md` §2.2.1）

**要求**：一台**有 root** 的手机 + 电脑上的 adb。

> 💡 下面的 `su -c "..."` 如果报错（有些 `su` 不把参数合并成一条命令），
> 换成 `adb shell "su -c '...'"`（外层双引号给设备 shell，里层单引号给 su）即可。

---

## 一、准备

```bash
# 电脑上（本目录）
adb devices                       # 确认 root 机器在线
adb push root_snapshot.sh /data/local/tmp/
adb shell su -c "chmod 755 /data/local/tmp/root_snapshot.sh"
```

如果机器上还没装游戏，先装一个底包（这两个就是为这件事做的）：

```bash
adb install -r 成品/Minecraft-0.2.0.25445-v20b-3px.apk     # 3px 那个
```

---

## 二、拍第一份快照（3px 状态）

```bash
# 1) 确保是【全新安装】：先卸载，再装 v20b（3px）
adb uninstall com.netease.mc.qihoo
adb install 成品/Minecraft-0.2.0.25445-v20b-3px.apk

# 2) 启动一次，让它建立玩家档案（进一次世界，或者进"皮肤"界面看一眼手臂是 3px）
adb shell am start -n com.netease.mc.qihoo/com.mojang.minecraftpe.MainActivity
#    …等它进到世界/皮肤界面，确认手臂是细的（3px）…

# 3) 退出游戏，拍快照
adb shell am force-stop com.netease.mc.qihoo
adb shell su -c "sh /data/local/tmp/root_snapshot.sh 3px"
adb pull /sdcard/dd_3px.tgz
```

## 三、拍第二份快照（4px 状态）

**重复上面整套，只把底包换成 v20a（4px）**：

```bash
adb uninstall com.netease.mc.qihoo
adb install 成品/Minecraft-0.2.0.25445-v20a-4px.apk
adb shell am start -n com.netease.mc.qihoo/com.mojang.minecraftpe.MainActivity
#    …确认手臂是粗的（4px）…
adb shell am force-stop com.netease.mc.qihoo
adb shell su -c "sh /data/local/tmp/root_snapshot.sh 4px"
adb pull /sdcard/dd_4px.tgz
```

> ⚠️ 两次之间**只许差手臂体型这一件事**：不要改名、不要换皮肤、不要动资源包、不要建多余的世界。
> 否则 diff 会多出一堆无关差异，反而难判断。

---

## 四、比对（电脑上）

```bash
mkdir -p dd_3px dd_4px
tar xzf dd_3px.tgz -C dd_3px
tar xzf dd_4px.tgz -C dd_4px
python ../mc-tool/tools/root_diff.py dd_3px dd_4px
```

脚本会打印：

* 新增 / 删除 / 内容变化的文件清单
* 变化的小文本文件的**逐行差异**
* 二进制文件里命中的关键字（`skin` / `geometry` / `slim` / `custom` / `alex` / `steve` …）

**判断**：改动**最小**的那个文件，基本就是玩家档案。

---

## 五、验证（关键一步）

找到候选文件后，用 root **只改它的体型字段**，重启游戏看手臂变没变：

```bash
# 例如候选是 files/xxx.json
adb shell su -c "cp /data/data/com.netease.mc.qihoo/files/xxx.json /sdcard/xxx.json.bak"
adb pull /data/data/com.netease.mc.qihoo/files/xxx.json   # 拉到电脑看/改
#   改完推回去（先退出游戏！）
adb push xxx.json /sdcard/
adb shell su -c "cp /sdcard/xxx.json /data/data/com.netease.mc.qihoo/files/xxx.json"
adb shell su -c "chown $(adb shell stat -c %u /data/data/com.netease.mc.qihoo/files) /data/data/com.netease.mc.qihoo/files/xxx.json"
adb shell am start -n com.netease.mc.qihoo/com.mojang.minecraftpe.MainActivity
```

**手臂跟着变了** ✔ → 找到了 ✔ → 那就可以写一个"改档案"的脚本（甚至让工具支持）
**没变** ✗ → 说明档案在 SQLite 或别的地方，把两份快照留下来，我接着分析 ✔

---

## 六、如果 diff 什么都没变

说明体型不在 `/data/data` 的普通文件里。剩下两个可能：

1. **SQLite 数据库**（`databases/*.db`）—— `root_snapshot.sh` 会一起打包，
   `root_diff.py` 也会报告它变了；用 `sqlite3` 或拉到电脑上看。
2. **世界/玩家存档里**（`Android/data/.../minecraftWorlds/<id>/db` 的 LevelDB，或 `level.dat`）
   —— 那样的话"换粗细"就只影响**新世界**，值得单独验一次：
   在同一个已装好的游戏中**新建一个世界**，看新世界的手臂是不是新粗细。
   （这一条**不需要 root**，也可以先在普通机器上做，见 README 里"仍未验证"第 1 条。）
