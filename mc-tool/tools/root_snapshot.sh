#!/system/bin/sh
# 在**有 root 的手机**上给游戏内部数据目录拍快照。
#
# 为什么要它：
#   手臂粗细（3px/4px）在"首次运行建立玩家档案"时被写死，之后改 APK 不生效
#   （见 mc-tool/README.md §2.2.1）。那个档案在 /data/data/com.netease.mc.qihoo/
#   里，**只有 root 能进** —— 所以要用这台 root 机器把它找出来。
#
# 用法（推到手机后）：
#   adb push root_snapshot.sh /data/local/tmp/
#   adb shell su -c "sh /data/local/tmp/root_snapshot.sh 3px"     # 装 3px 底包、首次运行后
#   ... 卸载、装 4px 底包、首次运行 ...
#   adb shell su -c "sh /data/local/tmp/root_snapshot.sh 4px"
#   adb pull /sdcard/dd_3px.tgz ; adb pull /sdcard/dd_4px.tgz
#   然后在电脑上跑 tools/root_diff.py dd_3px/ dd_4px/
#
# 注意：快照会把 /data/data 里所有普通文件打进去（一般几 MB ~ 几十 MB），
#       不含 cache（那个又大又没意义），但仍然**不要外传**（里面可能有账号信息）。

PKG=com.netease.mc.qihoo
TAG="${1:-snap}"
OUT="/sdcard/dd_${TAG}.tgz"

if [ "$(id -u)" != "0" ]; then
    echo "需要 root：请用 su -c 运行本脚本"
    exit 1
fi

DIR="/data/data/$PKG"
if [ ! -d "$DIR" ]; then
    echo "找不到 $DIR（游戏没装？）"
    exit 1
fi

echo "=== 快照 $TAG ==="
echo "  目录: $DIR"
echo "  游戏是否在跑: $(pidof $PKG >/dev/null 2>&1 && echo 是 || echo 否)"

# 先列出结构，方便人眼看
echo "--- 顶层 ---"
ls -la "$DIR"

rm -f "$OUT"
cd "$DIR" || exit 1
# 优先排除 cache（可重建、体积大）；老 tar 不认 --exclude 就退回全量打包
if tar czf "$OUT" --exclude=./cache --exclude=./code_cache . 2>/dev/null; then
    :
else
    echo "  （本机 tar 不支持 --exclude，改为全量打包）"
    tar czf "$OUT" .
fi

echo "--- 快照 ---"
ls -l "$OUT"
echo "  条目数: $(tar tzf "$OUT" 2>/dev/null | wc -l)"
echo
echo "接下来：adb pull $OUT"
