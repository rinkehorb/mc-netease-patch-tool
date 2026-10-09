# 03_sign_apk.ps1 —— 给重打包后的 APK 签名
#
# 背景：uber-apk-signer 1.3.0 在当前环境有两处坑，这里都已经绕开：
#   1) 它内置的 zipalign 在 Windows 上找不到 -> 用 --skipZipAlign，
#      对齐由 02_build_apk.py 自己做（zipalign 等价的 4 字节对齐）。
#   2) 它生成/落盘临时 debug keystore 时调用 File.createTempFile 会“拒绝访问”
#      -> 传 -Djava.io.tmpdir 指定一个可写目录即可。
#
# 用法：
#   powershell -File 03_sign_apk.ps1
#   powershell -File 03_sign_apk.ps1 -Apk .\patched\Minecraft-unsigned.apk
#
# 想用自己的密钥（需要 JDK 里的 keytool，本环境 github 不通拿不到 JDK，故未内置）：
#   keytool -genkeypair -keystore mc-patch.jks -alias mc -keyalg RSA -keysize 2048 `
#           -validity 10000 -storepass mcpatch123 -keypass mcpatch123 `
#           -dname "CN=MC Offline Patch, O=Local, C=CN"
#   powershell -File 03_sign_apk.ps1 -Ks mc-patch.jks -KsAlias mc -KsPass mcpatch123

param(
    [string]$Apk      = "$PSScriptRoot\patched\Minecraft-unsigned.apk",
    [string]$OutDir   = "$PSScriptRoot\patched\signed",
    [string]$Ks       = "",
    [string]$KsAlias  = "",
    [string]$KsPass   = "",
    [string]$KsKeyPass= ""
)

$ErrorActionPreference = 'Stop'

$java    = "$PSScriptRoot\tools\jre\jdk-17.0.20.1+1-jre\bin\java.exe"
$signer  = "$PSScriptRoot\tools\uber-apk-signer.jar"
$jtmp    = "$PSScriptRoot\jtmp"

foreach ($p in @($java, $signer, $Apk)) {
    if (-not (Test-Path $p)) { throw "找不到: $p" }
}
New-Item -ItemType Directory -Force -Path $OutDir, $jtmp | Out-Null

$signArgs = @("-Djava.io.tmpdir=$jtmp", "-jar", $signer,
          "-a", $Apk, "-o", $OutDir, "--allowResign", "--skipZipAlign", "--verbose")

if ($Ks -ne "") {
    $signArgs += @("--ks", $Ks, "--ksAlias", $KsAlias)
    if ($KsPass    -ne "") { $signArgs += @("--ksPass", $KsPass) }
    if ($KsKeyPass -ne "") { $signArgs += @("--ksKeyPass", $KsKeyPass) }
}

Write-Host "== 签名 ==" -ForegroundColor Cyan
& $java @signArgs
if ($LASTEXITCODE -ne 0) { throw "签名失败 (exit $LASTEXITCODE)" }

Write-Host "`n== 产物 ==" -ForegroundColor Cyan
Get-ChildItem $OutDir -Filter *.apk | ForEach-Object {
    $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    Write-Host ("{0}`n  {1} bytes`n  sha256 {2}" -f $_.FullName, $_.Length, $h)
}

Write-Host "`n== 纯校验（只验签，不再签名）==" -ForegroundColor Cyan
$apk = (Get-ChildItem $OutDir -Filter *.apk | Select-Object -First 1).FullName
& $java "-Djava.io.tmpdir=$jtmp" -jar $signer -a $apk --onlyVerify --skipZipAlign --verbose
