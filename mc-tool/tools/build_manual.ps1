# build_manual.ps1 —— 不依赖 Gradle / Android Studio 的手工构建
#
# 用到的工具（都在 tools\ 下，本仓库已备好）：
#   tools\jdk\...                     JDK 17（javac）
#   tools\android-sdk\build-tools\34.0.0\{aapt2,d8,zipalign,apksigner}
#   tools\android-sdk\platforms\android-34\android.jar
#   tools\lib\apksig-8.7.3.jar        （Gradle 路径下由依赖自动获取）
#   tools\debug.keystore              与 v19 同签名的密钥
#
# 用途：当你不想装 Android Studio、或者 Gradle 拉依赖出问题时，
#       这条路径能独立产出可安装的 APK。
#
# 用法： powershell -ExecutionPolicy Bypass -File tools\build_manual.ps1

# 注意：这里刻意用 Continue 而不是 Stop。
# javac / aapt2 / d8 都会往 stderr 打「注: ...已过时的 API」这类非错误信息，
# 而 PowerShell 在 $ErrorActionPreference='Stop' 时会把原生命令的 stderr
# 当成终止性错误直接中断脚本。每个关键步骤后面都手工检查 $LASTEXITCODE。
$ErrorActionPreference = 'Continue'

$Root = Split-Path -Parent $PSScriptRoot
$App  = Join-Path $Root 'app\src\main'
# 刻意不放在 build\ 下面：那是 Gradle 的地盘，`gradlew clean` 会把它整个删掉，
# 手工构建的产物会被顺手清掉。单独用一个 manual-build\ 目录。
$Bld  = Join-Path $Root 'manual-build'

$JdkDir = (Get-ChildItem (Join-Path $Root 'tools\jdk') -Directory | Select-Object -First 1).FullName
$Javac  = Join-Path $JdkDir 'bin\javac.exe'
$Jar    = Join-Path $JdkDir 'bin\jar.exe'
$Bt     = Join-Path $Root 'tools\android-sdk\build-tools\34.0.0'
$Aapt2  = Join-Path $Bt 'aapt2.exe'
$D8     = Join-Path $Bt 'd8.bat'
$ZipAl  = Join-Path $Bt 'zipalign.exe'
$ApkSig = Join-Path $Bt 'apksigner.bat'
$AndroidJar = Join-Path $Root 'tools\android-sdk\platforms\android-34\android.jar'
$ApksigJar  = Join-Path $Root 'tools\lib\apksig-8.7.3.jar'
$Ks     = Join-Path $Root 'tools\debug.keystore'
$Pkg    = 'com.mctool.mcpatch'

foreach ($p in @($Javac, $Aapt2, $D8, $ZipAl, $ApkSig, $AndroidJar, $ApksigJar, $Ks)) {
    if (-not (Test-Path $p)) { throw "缺少工具: $p" }
}

if (Test-Path $Bld) { Remove-Item $Bld -Recurse -Force }
New-Item -ItemType Directory -Force -Path "$Bld\gen","$Bld\classes","$Bld\dex" | Out-Null

Write-Host '== 1/6 预处理 AndroidManifest（补 package、替换 ${applicationId}）==' -ForegroundColor Cyan
$mf = Get-Content (Join-Path $App 'AndroidManifest.xml') -Raw
$mf = $mf.Replace('${applicationId}', $Pkg)
# AGP 8 的工程用的是 build.gradle 里的 namespace，清单里不写 package；
# 但 aapt2 必须有 package 属性，所以手工路径要补上。
if ($mf -notmatch 'package\s*=') {
    $mf = $mf.Replace('<manifest xmlns:android=', "<manifest package=`"$Pkg`" xmlns:android=")
}
Set-Content -Path "$Bld\AndroidManifest.xml" -Value $mf -Encoding UTF8
if ($mf -notmatch 'package\s*=') { throw '没能给 AndroidManifest 补上 package 属性' }

Write-Host '== 2/6 aapt2 compile 资源 ==' -ForegroundColor Cyan
& $Aapt2 compile --dir (Join-Path $App 'res') -o "$Bld\res.zip"
if ($LASTEXITCODE -ne 0) { throw 'aapt2 compile 失败' }

Write-Host '== 3/6 aapt2 link（生成资源表 + R.java + 打进 assets）==' -ForegroundColor Cyan
& $Aapt2 link `
    -o "$Bld\base.apk" `
    -I $AndroidJar `
    --manifest "$Bld\AndroidManifest.xml" `
    -A (Join-Path $App 'assets') `
    --java "$Bld\gen" `
    --custom-package $Pkg `
    --rename-manifest-package $Pkg `
    --min-sdk-version 26 `
    --target-sdk-version 34 `
    --version-code 261010 `
    --version-name 26.10.10 `
    "$Bld\res.zip"
if ($LASTEXITCODE -ne 0) { throw 'aapt2 link 失败' }

Write-Host '== 4/6 javac 编译 Java ==' -ForegroundColor Cyan
$srcs = @()
$srcs += Get-ChildItem (Join-Path $App 'java') -Recurse -Filter *.java | ForEach-Object { $_.FullName }
$srcs += Get-ChildItem "$Bld\gen" -Recurse -Filter *.java | ForEach-Object { $_.FullName }
$jout = & $Javac -encoding UTF-8 -nowarn -source 11 -target 11 `
    -cp "$AndroidJar;$ApksigJar" -d "$Bld\classes" @srcs 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Host $jout
    throw 'javac 失败'
}
Write-Host ("   源文件 {0} 个，class {1} 个" -f $srcs.Count,
    (Get-ChildItem "$Bld\classes" -Recurse -Filter *.class).Count)

Write-Host '== 5/6 d8 转 dex（含 apksig）==' -ForegroundColor Cyan
$classes = (Get-ChildItem "$Bld\classes" -Recurse -Filter *.class | ForEach-Object { $_.FullName })
$dout = & $D8 --lib $AndroidJar --min-api 26 --output "$Bld\dex" @classes $ApksigJar 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "$Bld\dex\classes.dex")) {
    Write-Host $dout
    throw 'd8 失败'
}
Write-Host ("   classes.dex {0} bytes" -f (Get-Item "$Bld\dex\classes.dex").Length)

Write-Host '== 6/6 打 dex 进 APK、对齐、签名 ==' -ForegroundColor Cyan
Copy-Item "$Bld\base.apk" "$Bld\unsigned.apk" -Force
# 用 System.IO.Compression 追加 classes.dex。
# 特意不用 `jar uf`：jar 会顺手塞一个 META-INF/MANIFEST.MF 进去，
# 之后 apksigner 的 v1 签名会和它对不上，导致 v1 校验失败。
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$Bld\unsigned.apk", 'Update')
try {
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $zip, "$Bld\dex\classes.dex", 'classes.dex',
        [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
} finally {
    $zip.Dispose()
}

# 顺带放一个 v1 需要的 META-INF 目录结构不用管，apksigner 自己会写
& $ZipAl -f -p 4 "$Bld\unsigned.apk" "$Bld\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw 'zipalign 失败' }

& $ApkSig sign `
    --ks $Ks --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android `
    --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true `
    --out "$Bld\MCPatchTool.apk" "$Bld\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw 'apksigner 失败' }

Write-Host ''
Write-Host '== 完成 ==' -ForegroundColor Green
& $ApkSig verify --print-certs "$Bld\MCPatchTool.apk" | Select-Object -First 6
Get-Item "$Bld\MCPatchTool.apk" | ForEach-Object {
    Write-Host ("输出: {0}`n  {1} bytes" -f $_.FullName, $_.Length)
}
