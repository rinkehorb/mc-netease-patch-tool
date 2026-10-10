#!/system/bin/sh
# 把 arm_switch.zip 放进游戏目录（测试「H5 自己覆盖 options.txt」用）。
# 正式用法应该走工具那套 MediaStore .png 通道，不需要 root —— 这里只是先验证机制。
D=/data/data/com.netease.mc.qihoo/games/com.netease
SRC=/data/local/tmp/arm_switch.zip
PE=$D/minecraftpe

if [ "$(id -u)" != "0" ]; then echo "需要 root"; exit 1; fi
if [ ! -f "$SRC" ]; then echo "缺少 $SRC"; exit 1; fi

echo "=== 覆盖前 ==="
grep -n game_skintypefull "$PE/options.txt"

cp -f "$SRC" "$D/arm_switch.zip"
chown 10271:10271 "$D/arm_switch.zip"
chmod 600 "$D/arm_switch.zip"

echo "=== zip 就位 ==="
ls -l "$D/arm_switch.zip"
echo "  zip 内容:"
unzip -l "$D/arm_switch.zip" 2>/dev/null || echo "  (本机没有 unzip，跳过列表)"
