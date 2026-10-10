#!/system/bin/sh
# 把一张皮肤图装成游戏的「自定义皮肤」，并确保手臂体型字段是想要的值。
# 需要 root。在手机上跑：
#   adb push custom_skin.png /data/local/tmp/custom_skin.png
#   adb shell su -c "sh /data/local/tmp/set_custom_skin.sh [Steve|Alex]"
#
# 依据：options.txt 里就是游戏原生的皮肤配置（root 才能看/改）
#   game_lastcustomskinnew:custom.png      自定义皮肤文件名
#   game_skintypefull:Standard_Steve      粗手臂 4px / Standard_Alex 细手臂 3px

DIR=/data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe
OPT=$DIR/options.txt
SRC=/data/local/tmp/custom_skin.png
TYPE="${1:-Steve}"

if [ "$(id -u)" != "0" ]; then
    echo "需要 root：用 su -c 运行"
    exit 1
fi
if [ ! -f "$OPT" ]; then
    echo "找不到 $OPT（游戏没装过？先启动一次）"
    exit 1
fi
if [ ! -f "$SRC" ]; then
    echo "找不到 $SRC（先把皮肤图 push 进去）"
    exit 1
fi

APP_UID=$(stat -c %u "$DIR")
APP_GID=$(stat -c %g "$DIR")
echo "=== 游戏数据目录属主: $APP_UID:$APP_GID ==="

# 0) 备份
cp -f "$OPT" /data/local/tmp/options.txt.bak 2>/dev/null && echo "  已备份 options.txt"

# 1) 装自定义皮肤（属主/权限必须和目录一致，否则游戏读不到）
cp -f "$SRC" "$DIR/custom.png"
chown "$APP_UID:$APP_GID" "$DIR/custom.png"
chmod 600 "$DIR/custom.png"

# 2) 打开开关 + 设置体型
sed -i "s/^game_lastcustomskinnew:.*/game_lastcustomskinnew:custom.png/" "$OPT"
sed -i "s/^game_skintypefull:.*/game_skintypefull:Standard_${TYPE}/" "$OPT"

echo "=== 结果 ==="
ls -l "$DIR/custom.png"
grep -n -e game_lastcustomskinnew -e game_skintypefull -e game_recentskin1 "$OPT"
