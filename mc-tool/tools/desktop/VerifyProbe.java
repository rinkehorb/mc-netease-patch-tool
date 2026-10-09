import com.mctool.mcpatch.core.ApkSignerHelper;

import java.io.File;

/**
 * 用<b>即将随包发布的 core 代码</b>（{@link ApkSignerHelper#inspectSigner}）
 * 验证源包签名检测，而不是探针里另写一遍逻辑。
 *
 * <p>用法： {@code java -cp ... VerifyProbe <apk> [apk2 ...]}
 */
public final class VerifyProbe {

    public static void main(String[] args) throws Exception {
        for (String a : args) {
            File apk = new File(a);
            System.out.println("=== " + apk.getName() + "  ("
                    + (apk.length() / 1048576) + " MB) ===");
            long t0 = System.currentTimeMillis();
            ApkSignerHelper.ApkSignerInfo info = ApkSignerHelper.inspectSigner(apk);
            long dt = System.currentTimeMillis() - t0;
            System.out.println("  耗时        : " + dt + " ms");
            System.out.println("  证书数      : " + info.certCount);
            System.out.println("  证书 SHA-256: " + info.certSha256);
            System.out.println("  校验通过    : " + info.verified
                    + "  (v1=" + info.v1 + " v2=" + info.v2 + " v3=" + info.v3 + ")");
            System.out.println("  与内置密钥一致: "
                    + ApkSignerHelper.V19_CERT_SHA256.equalsIgnoreCase(
                            info.certSha256 == null ? "" : info.certSha256));
            if (info.error != null) System.out.println("  错误        : " + info.error);
            System.out.println();
        }
    }
}
