#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 为改包工具生成你自己的签名密钥（Linux / macOS）
#
# 产出（给「改出来的游戏包」签名用）：
#   app/src/main/assets/mc-patch-key.pk8    PKCS#8 未加密 DER 私钥
#   app/src/main/assets/mc-patch-cert.pem   X.509 证书（PEM）
#
# 为什么要自己生成：仓库里只有一把【公用示例密钥】。更重要的是
# 【一旦你用某个密钥装过改包，以后就必须一直用同一个】—— 否则系统拒绝覆盖安装，
# 只能卸载重装，而卸载会删掉 Android/data（存档全没）。先想清楚再动手。
#
# 用法：
#   ./tools/genkey.sh                          # 生成自己的密钥
#   ./tools/genkey.sh --use-example-key        # 直接用仓库里的公用示例密钥
#   ALIAS=mykey PASS=mypass123 ./tools/genkey.sh
# ---------------------------------------------------------------------------
set -euo pipefail

ALIAS="${ALIAS:-mcpatch}"
PASSWORD="${PASSWORD:-mcpatch123}"
DNAME="${DNAME:-CN=MC Patch Tool, O=Local, C=CN}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
OUT_DIR="${OUT_DIR:-$ROOT/app/src/main/assets}"

KEY_FILE="$OUT_DIR/mc-patch-key.pk8"
CERT_FILE="$OUT_DIR/mc-patch-cert.pem"

# ---------------------------------------------------------------- 0. 示例密钥
if [ "${1:-}" = "--use-example-key" ]; then
  if [ ! -f "$OUT_DIR/mc-patch-key.pk8.example" ]; then
    echo "找不到示例密钥：$OUT_DIR/mc-patch-key.pk8.example" >&2
    exit 1
  fi
  cp "$OUT_DIR/mc-patch-key.pk8.example" "$KEY_FILE"
  cp "$OUT_DIR/mc-patch-cert.pem.example" "$CERT_FILE"
  echo
  echo "已复制【公用示例密钥】到 $OUT_DIR"
  echo "  注意：这把密钥是公开的，任何人都能签出可以覆盖安装到你手机上的包。"
  echo "  想用自己的密钥，就不带 --use-example-key 再跑一次。"
  exit 0
fi

# ---------------------------------------------------------------- 1. 找 JDK
find_jdk() {
  if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/keytool" ]; then echo "$JAVA_HOME"; return; fi
  if command -v keytool >/dev/null 2>&1; then
    local kt; kt="$(command -v keytool)"
    echo "$(dirname "$(dirname "$kt")")"; return
  fi
  for p in "$ROOT/tools/jdk" "$HERE/jdk"; do
    if [ -d "$p" ]; then
      local d; d="$(find "$p" -maxdepth 2 -type f -name keytool -path '*/bin/*' 2>/dev/null | head -1)"
      if [ -n "$d" ]; then echo "$(dirname "$(dirname "$d")")"; return; fi
    fi
  done
}
JDK="$(find_jdk || true)"
if [ -z "$JDK" ]; then
  echo "找不到 JDK（需要 keytool）。请设置 JAVA_HOME，或把 JDK 解压到 $ROOT/tools/jdk 下。" >&2
  exit 1
fi
echo "JDK      : $JDK"

mkdir -p "$OUT_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
KS="$TMP/mcpatch.p12"

# ---------------------------------------------------------------- 2. 生成密钥对
echo "生成 RSA 2048 密钥对并自签证书…"
"$JDK/bin/keytool" -genkeypair -v \
  -keystore "$KS" -storetype PKCS12 -alias "$ALIAS" \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass "$PASSWORD" -keypass "$PASSWORD" \
  -dname "$DNAME" >/dev/null

# ---------------------------------------------------------------- 3. 导出 pk8 + pem
mkdir -p "$TMP/classes"
"$JDK/bin/javac" -encoding UTF-8 -d "$TMP/classes" "$HERE/desktop/ExportKeyMaterial.java" 2>&1 |
  grep -v '^注:' || true
"$JDK/bin/java" -cp "$TMP/classes" ExportKeyMaterial "$KS" "$PASSWORD" "$ALIAS" "$PASSWORD" "$OUT_DIR" |
  sed 's/^/  /'

echo
echo "完成。两个文件已写到："
echo "  $KEY_FILE"
echo "  $CERT_FILE"
echo
echo "接下来："
echo "  1) 重新构建工具 APK（gradle build，或用 tools/build_manual.ps1）"
echo "  2) 【记住这把密钥】：以后每次改包都要用同一个，否则只能卸载重装（会丢存档）"
echo "  3) 最好把这两个文件另外备份一份"
