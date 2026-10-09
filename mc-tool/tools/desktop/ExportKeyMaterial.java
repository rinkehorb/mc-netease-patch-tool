import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.Base64;

/**
 * 把 JKS 里的签名材料导成两个「不依赖 KeyStore provider」的文件。
 *
 * <p>为什么要这么做：<b>Android 没有 JKS 实现</b>。
 * Android 支持的 KeyStore 类型只有 BKS / BKS-V1 / PKCS12 / AndroidKeyStore，
 * {@code KeyStore.getInstance("JKS")} 在真机上会抛
 * {@code KeyStoreException: JKS not found}（已实测）。
 * JKS 是 JDK 专有格式，所以桌面 JVM 上能跑、Robolectric 也能跑，
 * 一上真机就炸 —— 这类「宿主 JVM 与 Android 密码学不一致」的坑必须绕开。
 *
 * <p>导出的两个文件：
 * <ul>
 *   <li>{@code mc-patch-key.pk8} —— PKCS#8 未加密 DER 私钥</li>
 *   <li>{@code mc-patch-cert.pem} —— X.509 证书（PEM）</li>
 * </ul>
 * 读取时只需要 {@code KeyFactory.getInstance("RSA")} 与
 * {@code CertificateFactory.getInstance("X.509")}，
 * 这两个 provider 在 Android 和 JVM 上都一定存在。
 *
 * <p>用法：
 * <pre>java ExportKeyMaterial &lt;keystore&gt; &lt;storePass&gt; &lt;alias&gt; &lt;keyPass&gt; &lt;outDir&gt;</pre>
 */
public final class ExportKeyMaterial {

    public static void main(String[] args) throws Exception {
        if (args.length < 5) {
            System.err.println("用法: ExportKeyMaterial <keystore> <storePass> <alias> <keyPass> <outDir>");
            System.exit(2);
        }
        File ks = new File(args[0]);
        char[] storePass = args[1].toCharArray();
        String alias = args[2];
        char[] keyPass = args[3].toCharArray();
        File outDir = new File(args[4]);
        if (!outDir.isDirectory() && !outDir.mkdirs()) {
            throw new IllegalStateException("无法创建输出目录: " + outDir);
        }

        KeyStore keyStore = null;
        java.io.FileInputStream in = new java.io.FileInputStream(ks);
        try {
            // PKCS12 优先：keytool 从 JDK 9 起默认就是 PKCS12。
            // 两个 provider 在桌面 JVM 上都有，所以两种都能读。
            for (String type : new String[]{"PKCS12", "JKS"}) {
                try {
                    in.getChannel().position(0);
                    KeyStore candidate = KeyStore.getInstance(type);
                    candidate.load(in, storePass);
                    keyStore = candidate;
                    System.out.println("keystore 类型 : " + type);
                    break;
                } catch (Exception ignored) {
                    // 换下一种
                }
            }
        } finally {
            in.close();
        }
        if (keyStore == null) {
            throw new IllegalStateException("读不了这个 keystore（PKCS12/JKS 都试过了）: " + ks
                    + "\n  提示：口令错了、文件坏了，或者它是 BKS 等其它格式。");
        }

        if (!keyStore.isKeyEntry(alias)) {
            StringBuilder sb = new StringBuilder();
            java.util.Enumeration<String> en = keyStore.aliases();
            while (en.hasMoreElements()) sb.append(en.nextElement()).append(' ');
            throw new IllegalStateException("别名 " + alias + " 不是私钥条目。可用别名: " + sb);
        }

        PrivateKey key = (PrivateKey) keyStore.getKey(alias, keyPass);
        Certificate[] chain = keyStore.getCertificateChain(alias);
        if (chain == null || chain.length == 0) throw new IllegalStateException("没有证书链");

        byte[] pk8 = key.getEncoded();
        if (pk8 == null || !"PKCS#8".equalsIgnoreCase(key.getFormat())) {
            throw new IllegalStateException("私钥编码格式不是 PKCS#8: " + key.getFormat());
        }
        File keyFile = new File(outDir, "mc-patch-key.pk8");
        FileOutputStream kos = new FileOutputStream(keyFile);
        try {
            kos.write(pk8);
        } finally {
            kos.close();
        }

        // 证书链：第一张是签名证书，其余是中间 CA（这个 debug 证书链只有一张）
        StringBuilder pem = new StringBuilder();
        for (Certificate c : chain) {
            pem.append("-----BEGIN CERTIFICATE-----\n");
            String b64 = Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.US_ASCII))
                    .encodeToString(c.getEncoded());
            pem.append(b64).append('\n');
            pem.append("-----END CERTIFICATE-----\n");
        }
        File certFile = new File(outDir, "mc-patch-cert.pem");
        Writer w = new OutputStreamWriter(new FileOutputStream(certFile), StandardCharsets.US_ASCII);
        try {
            w.write(pem.toString());
        } finally {
            w.close();
        }

        X509Certificate leaf = (X509Certificate) chain[0];
        byte[] fp = java.security.MessageDigest.getInstance("SHA-256").digest(leaf.getEncoded());
        StringBuilder hex = new StringBuilder();
        for (byte b : fp) hex.append(String.format("%02X", b));

        System.out.println("私钥算法 : " + key.getAlgorithm() + " / " + key.getFormat());
        System.out.println("私钥文件 : " + keyFile.getAbsolutePath() + "  (" + keyFile.length() + " B)");
        System.out.println("证书文件 : " + certFile.getAbsolutePath() + "  (" + certFile.length() + " B)");
        System.out.println("证书链长 : " + chain.length);
        System.out.println("证书主体 : " + leaf.getSubjectX500Principal().getName());
        System.out.println("SHA-256  : " + hex);
        System.out.println("与 v19 一致: " + "1E08A903AEF9C3A721510B64EC764D01D3D094EB954161B62544EA8F187B5953".equalsIgnoreCase(hex.toString()));
    }
}
