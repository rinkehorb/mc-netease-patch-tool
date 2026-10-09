package com.mctool.mcpatch.core;

import com.android.apksig.ApkSigner;
import com.android.apksig.ApkSigner.SignerConfig;
import com.android.apksig.ApkVerifier;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;

/**
 * 用 Google 官方的 {@code apksig} 库做 v1 + v2 + v3 签名（就是 apksigner 的内核）。
 *
 * <h3>为什么不用 KeyStore</h3>
 * Android <b>没有 JKS 实现</b>：它只支持 BKS / BKS-V1 / PKCS12 / AndroidKeyStore。
 * 一开始这里用的是 {@code KeyStore.getInstance("JKS")}，在 PC 与 Robolectric 上全部正常，
 * 一装到真机就在签名阶段抛 {@code KeyStoreException: JKS not found}。
 *
 * <p>现在改成直接吃「PKCS#8 私钥 + X.509 证书」的原始字节，
 * 解析只需要 {@code KeyFactory.getInstance("RSA")} 和
 * {@code CertificateFactory.getInstance("X.509")} —— 这两个 provider
 * Android 与 JVM 都一定有，不会再有宿主环境差异。
 *
 * <h3>内置密钥</h3>
 * 沿用 v19 用的那把 Android debug key
 * （证书 SHA-256 {@code 1E08A903…5953}），于是产出包和 v19 <b>同包名同签名</b>，
 * 可以直接覆盖安装，不用卸载、不丢存档。
 */
public final class ApkSignerHelper {

    /** v19 的签名证书指纹，用来判断产出能不能直接覆盖安装。 */
    public static final String V19_CERT_SHA256 =
            "1E08A903AEF9C3A721510B64EC764D01D3D094EB954161B62544EA8F187B5953";

    /**
     * 仓库里那把<b>公用示例密钥</b>的指纹（{@code assets/*.example}）。
     *
     * <p>它是公开的：谁都能用它签出「可以覆盖安装到别人手机上」的包。
     * 所以用它构建出来的工具要在界面上明确提醒 —— 自己长期用的话应该跑
     * {@code tools/genkey.ps1} 换一把只有自己知道的。
     */
    public static final String EXAMPLE_CERT_SHA256 =
            "4AE02588CCEA0BDB158FB4C88BAC6A46708DC99F28253FA6C18DF3C10EAA3D14";

    private static final String PEM_BEGIN = "-----BEGIN CERTIFICATE-----";
    private static final String PEM_END = "-----END CERTIFICATE-----";

    private ApkSignerHelper() {
    }

    // ------------------------------------------------------------------ 签名材料解析

    /** 从 PKCS#8 DER 还原 RSA 私钥。 */
    public static PrivateKey loadPrivateKey(byte[] pkcs8) throws Exception {
        if (pkcs8 == null || pkcs8.length == 0) {
            throw new IllegalArgumentException("私钥字节为空");
        }
        return KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(pkcs8));
    }

    /** 从 PEM 或 DER 解析证书链（PEM 里可以有多个块）。 */
    public static List<X509Certificate> loadCertificates(byte[] cert) throws Exception {
        if (cert == null || cert.length == 0) {
            throw new IllegalArgumentException("证书字节为空");
        }
        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        List<X509Certificate> out = new ArrayList<X509Certificate>();

        String text = new String(cert, StandardCharsets.US_ASCII);
        if (text.indexOf(PEM_BEGIN) >= 0) {
            int idx = 0;
            while (true) {
                int b = text.indexOf(PEM_BEGIN, idx);
                if (b < 0) break;
                int e = text.indexOf(PEM_END, b);
                if (e < 0) break;
                String b64 = text.substring(b + PEM_BEGIN.length(), e).replaceAll("\\s", "");
                byte[] der = Base64.getDecoder().decode(b64);
                out.add((X509Certificate) cf.generateCertificate(new ByteArrayInputStream(der)));
                idx = e + PEM_END.length();
            }
        } else {
            out.add((X509Certificate) cf.generateCertificate(new ByteArrayInputStream(cert)));
        }
        if (out.isEmpty()) {
            throw new IllegalStateException("证书里没有可用的 X.509 条目");
        }
        return out;
    }

    /**
     * 自检：把私钥和证书都真解析一遍，返回签名证书的 SHA-256（大写无冒号）。
     * 界面启动时和开始生成前都会调它，好在浪费几十秒拷 APK 之前就发现问题。
     */
    public static String selfTest(PatchSpec spec) throws Exception {
        loadPrivateKey(spec.signerPrivateKeyPkcs8);
        List<X509Certificate> certs = loadCertificates(spec.signerCertificate);
        return sha256Hex(certs.get(0).getEncoded());
    }

    public static boolean matchesV19(PatchSpec spec) throws Exception {
        return V19_CERT_SHA256.equalsIgnoreCase(selfTest(spec));
    }

    /** 当前用的是不是仓库里那把公开的示例密钥。 */
    public static boolean matchesExampleKey(PatchSpec spec) throws Exception {
        return EXAMPLE_CERT_SHA256.equalsIgnoreCase(selfTest(spec));
    }

    private static String sha256Hex(byte[] data) throws Exception {
        byte[] d = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder sb = new StringBuilder(d.length * 2);
        for (byte b : d) sb.append(String.format("%02X", b));
        return sb.toString();
    }

    // ------------------------------------------------------------------ 读源包签名

    /** 源 APK 的签名情况。 */
    public static final class ApkSignerInfo {
        /** 签名证书 SHA-256（大写无冒号）；读不出来时为 null。 */
        public String certSha256;
        /** v1/v2/v3 任一通过校验。 */
        public boolean verified;
        public boolean v1, v2, v3;
        public int certCount;
        public String error;

        public boolean hasCert() {
            return certSha256 != null;
        }
    }

    /**
     * 读出一个 APK 的签名证书指纹 —— 用来判断「产出包能不能直接覆盖安装」。
     *
     * <p>为什么用 apksig 的 {@code ApkVerifier} 而不是 Android 的
     * {@code PackageManager.getPackageArchiveInfo}：
     * <ul>
     *   <li>后者受 Android 11+ 的<b>包可见性</b>规则影响，可能直接返回 null，
     *       那就白做了；apksig 是自己解析归档，不受影响。</li>
     *   <li>apksig 还顺带告诉你签名是否真的通过校验，信息更完整。</li>
     *   <li>它是纯 Java，能放进 core 里在 PC 上验证 —— 不用靠真机试。</li>
     * </ul>
     *
     * <p>只查 v2/v3（平台 28..34），跳过最慢的 v1 JAR 全量摘要。
     * 实测 157 MB 的包在 PC 上约 250 ms，手机上估计 1~3 秒，放在后台体检里可接受。
     */
    public static ApkSignerInfo inspectSigner(File apk) {
        ApkSignerInfo info = new ApkSignerInfo();
        try {
            ApkVerifier.Result r = new ApkVerifier.Builder(apk)
                    .setMinCheckedPlatformVersion(28)
                    .setMaxCheckedPlatformVersion(34)
                    .build()
                    .verify();
            info.verified = r.isVerified();
            info.v1 = r.isVerifiedUsingV1Scheme();
            info.v2 = r.isVerifiedUsingV2Scheme();
            info.v3 = r.isVerifiedUsingV3Scheme();
            List<X509Certificate> certs = r.getSignerCertificates();
            if (certs != null && !certs.isEmpty()) {
                info.certCount = certs.size();
                info.certSha256 = sha256Hex(certs.get(0).getEncoded());
            } else if (r.containsErrors()) {
                info.error = String.valueOf(r.getErrors());
            }
        } catch (Throwable t) {
            info.error = String.valueOf(t.getMessage());
        }
        return info;
    }

    // ------------------------------------------------------------------ 签名

    public static void sign(PatchSpec spec, File in, File out) throws Exception {
        PrivateKey key = loadPrivateKey(spec.signerPrivateKeyPkcs8);
        List<X509Certificate> certs = loadCertificates(spec.signerCertificate);

        // 注意：apksig 8.x 里 v1/v2/v3 开关挂在 ApkSigner.Builder 上，
        // SignerConfig.Builder 只负责「用哪把钥匙 + 证书链」。
        SignerConfig signerConfig = new SignerConfig.Builder("mcpatch", key, certs).build();

        ApkSigner signer = new ApkSigner.Builder(Collections.singletonList(signerConfig))
                .setInputApk(in)
                .setOutputApk(out)
                .setMinSdkVersion(spec.signMinSdkVersion)
                .setV1SigningEnabled(spec.v1Signing)
                .setV2SigningEnabled(spec.v2Signing)
                .setV3SigningEnabled(spec.v3Signing)
                .setV4SigningEnabled(false)
                .setOtherSignersSignaturesPreserved(false)
                .build();
        signer.sign();
    }
}
