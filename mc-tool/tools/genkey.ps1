<#
.SYNOPSIS
    为改包工具生成你自己的签名密钥。

.DESCRIPTION
    工具给「改出来的游戏包」签名用的一对文件：
        app/src/main/assets/mc-patch-key.pk8    PKCS#8 未加密 DER 私钥
        app/src/main/assets/mc-patch-cert.pem   X.509 证书（PEM）

    为什么要你自己生成（而不是用仓库里带的）：
      * 仓库里只有一把【公用的示例密钥】。用它签出来的包，别人也能签出「能覆盖安装到你手机上」的包。
      * 更重要的是：一旦你用某个密钥装过改包，以后就必须一直用同一个密钥，
        否则系统会拒绝覆盖安装，只能卸载重装 —— 而卸载会删掉 Android/data，你的存档就没了。
        所以【先想清楚，再动手】。

    需要 JDK（有 keytool 就行）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\genkey.ps1
    powershell -ExecutionPolicy Bypass -File tools\genkey.ps1 -Alias mykey -Password mypass123
#>
[CmdletBinding()]
param(
    [string]$Alias = "mcpatch",
    [string]$Password = "mcpatch123",
    [string]$DName = "CN=MC Patch Tool, O=Local, C=CN",
    [string]$OutDir,
    [switch]$UseExampleKey
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot          # mc-tool/
if (-not $OutDir) { $OutDir = Join-Path $root "app\src\main\assets" }

$keyFile = Join-Path $OutDir "mc-patch-key.pk8"
$certFile = Join-Path $OutDir "mc-patch-cert.pem"

# ---------------------------------------------------------------- 0. 用示例密钥？
if ($UseExampleKey) {
    $ex1 = Join-Path $OutDir "mc-patch-key.pk8.example"
    $ex2 = Join-Path $OutDir "mc-patch-cert.pem.example"
    if (-not (Test-Path $ex1) -or -not (Test-Path $ex2)) {
        throw "找不到示例密钥（$ex1）。"
    }
    Copy-Item $ex1 $keyFile -Force
    Copy-Item $ex2 $certFile -Force
    Write-Host ""
    Write-Host "已复制【公用示例密钥】到 $OutDir" -ForegroundColor Yellow
    Write-Host "  注意：这把密钥是公开的，任何人拿到后都能签出可以覆盖安装到你手机上的包。" -ForegroundColor Yellow
    Write-Host "  想用自己的密钥，就不带 -UseExampleKey 再跑一次。" -ForegroundColor Yellow
    exit 0
}

# ---------------------------------------------------------------- 1. 找 JDK
function Find-Jdk {
    if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME "bin\keytool.exe"))) { return $env:JAVA_HOME }
    if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME "bin/keytool"))) { return $env:JAVA_HOME }
    $cmd = Get-Command keytool -ErrorAction SilentlyContinue
    if ($cmd) { return (Split-Path -Parent (Split-Path -Parent $cmd.Source)) }
    foreach ($p in @("$root\tools\jdk", "$PSScriptRoot\jdk")) {
        if (Test-Path $p) {
            $d = Get-ChildItem $p -Directory -ErrorAction SilentlyContinue |
                 Where-Object { Test-Path (Join-Path $_.FullName "bin\keytool.exe") } |
                 Select-Object -First 1
            if ($d) { return $d.FullName }
        }
    }
    return $null
}

$jdk = Find-Jdk
if (-not $jdk) {
    throw "找不到 JDK（需要 keytool）。请设置 JAVA_HOME，或把 JDK 解压到 $root\tools\jdk 下。"
}
$keytool = Join-Path $jdk "bin\keytool.exe"
if (-not (Test-Path $keytool)) { $keytool = Join-Path $jdk "bin/keytool" }
$javac = Join-Path $jdk "bin\javac.exe"
if (-not (Test-Path $javac)) { $javac = Join-Path $jdk "bin/javac" }
$java = Join-Path $jdk "bin\java.exe"
if (-not (Test-Path $java)) { $java = Join-Path $jdk "bin/java" }
Write-Host "JDK      : $jdk"

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

# ---------------------------------------------------------------- 2. 生成密钥对
# 注意：keytool / javac 这些原生命令会把正常输出写到 stderr，
# 在 $ErrorActionPreference='Stop' 下会被当成错误。这两个调用期间放宽一下。
$ErrorActionPreference = "Continue"
# 临时目录放在仓库里而不是系统 TEMP：
#   ① 某些环境（沙箱、受限账户）不让写系统临时目录，keytool 会直接失败；
#   ② 顺带避免把私钥留在 %TEMP% 里。
$tmp = Join-Path $root ".genkey-tmp"
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$ks = Join-Path $tmp "mcpatch.p12"
try {
    Write-Host "生成 RSA 2048 密钥对并自签证书…"
    # 提示：-dname 用逗号分隔字段，所以字段值里【不能再出现逗号】（踩过）。
    & $keytool -genkeypair -v `
        -keystore $ks -storetype PKCS12 -alias $Alias `
        -keyalg RSA -keysize 2048 -validity 10000 `
        -storepass $Password -keypass $Password `
        -dname $DName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "keytool 失败（退出码 $LASTEXITCODE）。检查 -DName 里是不是有逗号。" }
    if (-not (Test-Path $ks)) { throw "keytool 没有生成 keystore" }

    # ------------------------------------------------------------ 3. 导出成 pk8 + pem
    $cls = Join-Path $tmp "classes"
    New-Item -ItemType Directory -Force -Path $cls | Out-Null
    & $javac -encoding UTF-8 -d $cls (Join-Path $PSScriptRoot "desktop\ExportKeyMaterial.java") 2>&1 |
        Where-Object { $_ -notmatch '^注:' } | ForEach-Object { "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "编译 ExportKeyMaterial 失败" }

    & $java -cp $cls ExportKeyMaterial $ks $Password $Alias $Password $OutDir 2>&1 |
        ForEach-Object { "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "导出签名材料失败" }
} finally {
    $ErrorActionPreference = "Stop"
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "完成。两个文件已写到：" -ForegroundColor Green
Write-Host "  $keyFile"
Write-Host "  $certFile"
Write-Host ""
Write-Host "接下来：" -ForegroundColor Cyan
Write-Host "  1) 重新构建工具 APK（Gradle，或用 tools\build_manual.ps1）"
Write-Host "  2) 【记住这把密钥】：以后每次改包都要用同一个，否则只能卸载重装（会丢存档）"
Write-Host "  3) 最好把这两个文件另外备份一份（比如加密压缩包）"
