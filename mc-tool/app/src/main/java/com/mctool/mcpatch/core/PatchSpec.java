package com.mctool.mcpatch.core;

import java.io.File;

/**
 * 「要改什么」的参数集合。纯 Java，无 Android 依赖
 * —— 同一份代码既跑在手机上，也能在桌面 JVM 上跑，方便离线验证产物是否正确。
 */
public final class PatchSpec {

    /** 源 APK（必须是本地真实文件，ZipFile 需要随机访问）。 */
    public File srcApk;
    /** 输出 APK。 */
    public File dstApk;

    // ---------------- 玩家名称（改 assets/resource_packs/vanilla/texts/*.lang 的 skin.name.*）
    public boolean renameEnabled;
    /** 要写入的名字，非空。 */
    public String playerName;

    // ---------------- 皮肤
    public boolean skinEnabled;
    /** 皮肤 PNG 的原始字节，尺寸必须是 64x64 或 128x128。 */
    public byte[] skinPng;
    /** true = 细手臂(Alex, geometry.humanoid.customSlim)；false = 粗手臂(Steve, geometry.humanoid.custom)。 */
    public boolean slimArms = true;

    // ---------------- 资源包
    public boolean packEnabled;
    /**
     * 要叠加的资源包，<b>按顺序</b>应用：后面的覆盖前面的同名文件。
     * {@code texts/*.lang} 走追加合并，所以后面的包翻译优先。
     */
    public java.util.List<File> resourcePacks = new java.util.ArrayList<File>();

    // ---------------- 导入界面（注入 assets/web/index.html）
    /**
     * 要注入到游戏 H5 的 JS 片段（工具 APK 的 {@code assets/mc-import.js}）。
     *
     * <p>为什么要注入：网易版的世界列表是一个网页，它读的是网易自己的「世界记录」，
     * 不是扫目录；而 H5 能调的 {@code h5adaptor.decompress_map} 目标目录任意，
     * 于是可以在网页里加一个「导入世界」按钮，把世界和记录一起写进去 ——
     * <b>全程不需要 root</b>。见 README 第 9 节。
     *
     * <p>为 null 或空 = 不注入。注入后 {@code index.html} 末尾会多一段
     * {@code <script>}，其余内容不变。
     */
    public byte[] importScript;

    // ---------------- 签名材料
    //
    // 刻意不走 KeyStore，而是直接给「PKCS#8 私钥 + X.509 证书」的原始字节。
    //
    // 原因（真机实测踩过）：Android 没有 JKS 实现，支持的 KeyStore 类型只有
    // BKS / BKS-V1 / PKCS12 / AndroidKeyStore，
    // KeyStore.getInstance("JKS") 在手机上直接抛 KeyStoreException: JKS not found。
    // 而 JKS 在桌面 JVM 和 Robolectric 里都是好的 —— 于是出现
    // 「PC 全绿、装到手机一签名就失败」这种最难查的偏差。
    //
    // 用原始字节解析只需要 KeyFactory("RSA") 与 CertificateFactory("X.509")，
    // 这两个 provider 在 Android 与 JVM 上都一定存在，彻底消除差异。

    /** PKCS#8 未加密 DER 私钥（assets/mc-patch-key.pk8）。 */
    public byte[] signerPrivateKeyPkcs8;
    /** X.509 证书，PEM 或 DER 均可（assets/mc-patch-cert.pem）。 */
    public byte[] signerCertificate;

    /** 用于让 apksig 决定 v1 摘要算法；19 = 兼容 Android 4.4 起全部版本。 */
    public int signMinSdkVersion = 19;
    public boolean v1Signing = true;
    public boolean v2Signing = true;
    public boolean v3Signing = true;

    public void validate() {
        if (srcApk == null || !srcApk.isFile()) throw new IllegalArgumentException("请先选择源 APK");
        if (dstApk == null) throw new IllegalArgumentException("缺少输出路径");
        if (srcApk.getAbsolutePath().equals(dstApk.getAbsolutePath()))
            throw new IllegalArgumentException("输出文件不能和源 APK 是同一个文件");
        if (renameEnabled && (playerName == null || playerName.trim().isEmpty()))
            throw new IllegalArgumentException("已勾选改名，但名字是空的");
        if (renameEnabled && (playerName.indexOf('=') >= 0 || playerName.indexOf('\n') >= 0
                || playerName.indexOf('\r') >= 0 || playerName.indexOf('\t') >= 0))
            throw new IllegalArgumentException("名字里不能包含 = 换行 或 Tab 字符（会破坏 lang 文件格式）");
        if (skinEnabled && (skinPng == null || skinPng.length == 0))
            throw new IllegalArgumentException("已勾选换皮肤，但没有选到图片");
        if (packEnabled) {
            if (resourcePacks == null || resourcePacks.isEmpty())
                throw new IllegalArgumentException("已勾选换资源包，但没有选到文件");
            for (File f : resourcePacks) {
                if (f == null || !f.isFile())
                    throw new IllegalArgumentException("资源包不存在: " + f);
            }
        }
        if (signerPrivateKeyPkcs8 == null || signerPrivateKeyPkcs8.length == 0)
            throw new IllegalArgumentException("缺少签名私钥（mc-patch-key.pk8 没读到）");
        if (signerCertificate == null || signerCertificate.length == 0)
            throw new IllegalArgumentException("缺少签名证书（mc-patch-cert.pem 没读到）");
    }

    /** 至少要改一样东西。 */
    public boolean hasAnyChange() {
        return renameEnabled || skinEnabled || packEnabled
                || (importScript != null && importScript.length > 0);
    }
}
