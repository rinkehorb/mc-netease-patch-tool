import com.mctool.mcpatch.core.ApkPatcher;
import com.mctool.mcpatch.core.ApkSignerHelper;
import com.mctool.mcpatch.core.PatchLog;
import com.mctool.mcpatch.core.PatchSpec;

import java.io.File;

/**
 * 桌面验证夹具：在 PC 的 JVM 上跑 <b>和手机 App 完全相同</b> 的 core 代码，
 * 产出一个真实 APK，然后用 apksigner / Python 独立验签与逐项比对。
 *
 * <p>用法：
 * <pre>
 * java -cp out;apksig.jar DesktopHarness &lt;srcApk&gt; &lt;outApk&gt; &lt;assetsDir&gt; \
 *      &lt;playerName|-> &lt;skin.png|-> &lt;slim|classic&gt; &lt;resourcepack.zip|-&gt;
 * </pre>
 * {@code assetsDir} 里要有 {@code mc-patch-key.pk8} 与 {@code mc-patch-cert.pem}
 * （由 {@code ExportKeyMaterial} 从 JKS 导出）。
 */
public final class DesktopHarness {

    public static void main(String[] args) throws Exception {
        if (args.length < 7) {
            System.err.println("用法: DesktopHarness <srcApk> <outApk> <assetsDir> <name|-> <skin.png|-> <slim|classic> <pack.zip|->");
            System.exit(2);
        }
        File assetsDir = new File(args[2]);
        PatchSpec spec = new PatchSpec();
        spec.srcApk = new File(args[0]);
        spec.dstApk = new File(args[1]);
        spec.signerPrivateKeyPkcs8 = ApkPatcher.readFile(new File(assetsDir, "mc-patch-key.pk8"));
        spec.signerCertificate = ApkPatcher.readFile(new File(assetsDir, "mc-patch-cert.pem"));

        if (!"-".equals(args[3])) {
            spec.renameEnabled = true;
            spec.playerName = args[3];
        }
        if (!"-".equals(args[4])) {
            spec.skinEnabled = true;
            spec.skinPng = ApkPatcher.readFile(new File(args[4]));
            int[] sz = ApkPatcher.pngSize(spec.skinPng);
            System.out.println("[harness] 皮肤尺寸 = " + (sz == null ? "非 PNG" : sz[0] + "x" + sz[1]));
        }
        spec.slimArms = !"classic".equalsIgnoreCase(args[5]);
        if (!"-".equals(args[6])) {
            spec.packEnabled = true;
            // 多个资源包用 ';' 分隔，按顺序叠加
            for (String p : args[6].split(";")) {
                if (!p.trim().isEmpty()) spec.resourcePacks.add(new File(p.trim()));
            }
            System.out.println("[harness] 资源包 " + spec.resourcePacks.size() + " 个（按顺序叠加）");
        }
        // 第 8 个参数（可选）：要注入到游戏 H5 首页的导入界面脚本
        if (args.length >= 8 && !"-".equals(args[7])) {
            spec.importScript = ApkPatcher.readFile(new File(args[7]));
            System.out.println("[harness] 注入导入界面 " + spec.importScript.length + " 字节");
        }

        String fp = ApkSignerHelper.selfTest(spec);
        System.out.println("[harness] 内置签名证书 SHA-256 = " + fp);
        System.out.println("[harness] 与 v19 一致 = " + ApkSignerHelper.matchesV19(spec));

        PatchLog log = new PatchLog() {
            @Override
            public void stage(String text) {
                System.out.println("[stage] " + text);
            }

            @Override
            public void detail(String text) {
                System.out.println("        " + text);
            }

            @Override
            public void progress(double fraction) {
                // 安静模式
            }
        };

        ApkPatcher.Result r = ApkPatcher.patch(spec, log);
        System.out.println();
        System.out.println("[result] " + r);
        System.out.println("[result] 源 " + r.srcSize + " B -> 出 " + r.outSize + " B, 耗时 " + r.millis + " ms");
        System.out.println("[result] 皮肤文件 " + r.skinFiles + " 个, 资源包文件 " + r.resourcePackFiles + " 个");
        System.out.println("[result] 导入界面已注入 = " + r.importUiInjected);
    }
}
