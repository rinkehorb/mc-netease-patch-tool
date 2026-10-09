package com.mctool.mcpatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.os.Looper;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.RadioButton;
import android.widget.TextView;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.Shadows;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;

/**
 * 框架级测试：在 JVM 上跑真实的 Android 框架代码，把 MainActivity 真的创建起来。
 *
 * <p>覆盖「装上去一打开就崩」这一类最致命的问题：
 * <ul>
 *   <li>主题能不能解析、布局能不能膨胀；</li>
 *   <li>{@code findViewById} 的每个控件是否真的存在（id 对不上就会 NPE）；</li>
 *   <li>内置签名材料能不能读出来，指纹是不是改包那把；</li>
 *   <li>勾选框联动、以及<b>选择记忆</b>（重建 Activity 后能不能恢复）。</li>
 * </ul>
 *
 * <p><b>能力边界</b>：Robolectric 跑在宿主 JVM 上，用的是 JVM 的密码学实现，
 * 不是 Android 的 Conscrypt，所以它证明不了「Android 上某个 provider 一定存在」。
 * 真机上报过的 {@code JKS not found} 就是这类偏差 —— 那个坑的修法是
 * 从设计上不依赖可能缺失的 provider（只用 PKCS#8 + X.509），不是加测试。
 * 它同样不覆盖 SAF 选文件、后台线程、调起安装器这三块，那些需要真机。
 */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34)
public class MainActivityLaunchTest {

    /** 布局里所有会被代码引用的 id，漏一个就是运行时 NPE。 */
    private static final int[] ALL_IDS = {
            R.id.btnPickApk, R.id.tvApk, R.id.tvSourceInfo,
            R.id.cbRename, R.id.etName, R.id.btnClearName,
            R.id.cbSkin, R.id.btnPickSkin, R.id.ivSkin, R.id.tvSkin,
            R.id.rgArms, R.id.rbSlim, R.id.rbClassic,
            R.id.cbPack, R.id.btnPickPack, R.id.btnClearPack, R.id.tvPack,
            R.id.tvSign, R.id.btnGenerate, R.id.cbAutoExport, R.id.progress, R.id.tvStatus,
            R.id.btnInstall, R.id.btnCopyLog,
            R.id.btnPickImport, R.id.tvImport, R.id.btnDoImport, R.id.cbDowngrade,
            R.id.tvLog, R.id.tvCredit,
    };

    private static ActivityController<MainActivity> launch() {
        ActivityController<MainActivity> c = Robolectric.buildActivity(MainActivity.class);
        c.setup();
        Shadows.shadowOf(Looper.getMainLooper()).idle();
        return c;
    }

    @Test
    public void activityInflatesAndEveryIdResolves() {
        ActivityController<MainActivity> c = launch();
        MainActivity a = c.get();
        assertNotNull(a);

        for (int id : ALL_IDS) {
            String name = a.getResources().getResourceName(id);
            assertNotNull("布局里找不到控件: " + name, a.findViewById(id));
        }

        c.pause().stop().destroy();
    }

    /**
     * 签名材料：三种状态都必须被正确处理，而不是写死某一把密钥。
     *
     * <p>为什么要这样写：<b>公开仓库里刻意不带私钥</b>（只有 {@code *.example} 的
     * 公用示例密钥），所以同一份代码会有三种合法状态：
     * <ol>
     *   <li>还没生成密钥 —— 必须给出<b>可操作</b>的提示（去哪里生成），而不是一句报错；</li>
     *   <li>用的是公开示例密钥 —— 必须明确告警；</li>
     *   <li>用的是自己的密钥 —— 正常运行（指纹是否与某个特定改包一致是<b>动态</b>算的）。</li>
     * </ol>
     * 早先这里写死了 {@code 1E08A903}，结果换个密钥构建测试就红 ——
     * 那是测试的错，不是代码的错。
     */
    @Test
    public void signerMaterialHandlesAllThreeStates() {
        ActivityController<MainActivity> c = launch();
        MainActivity a = c.get();
        String log = ((TextView) a.findViewById(R.id.tvLog)).getText().toString();
        String sign = ((TextView) a.findViewById(R.id.tvSign)).getText().toString();

        boolean hasKey = assetExists(a, "mc-patch-key.pk8");
        boolean hasCert = assetExists(a, "mc-patch-cert.pem");
        assertEquals("两个签名材料要么都在、要么都不在（缺了就说明还没生成密钥）",
                hasKey, hasCert);

        if (!hasKey) {
            assertTrue("缺少签名材料时必须告诉他怎么生成，而不是只说读取失败。实际:\n" + log,
                    log.contains("genkey"));
            assertTrue("界面上也应给出生成指引，实际: " + sign, sign.contains("genkey"));
            c.pause().stop().destroy();
            return;
        }

        // 有材料：日志里必须打印 64 位十六进制指纹
        java.util.regex.Matcher m = java.util.regex.Pattern
                .compile("签名证书 SHA-256[:：]\\s*([0-9A-Fa-f]{64})").matcher(log);
        assertTrue("启动日志里应打印 64 位证书指纹，实际为:\n" + log, m.find());
        String fp = m.group(1).toUpperCase(java.util.Locale.ROOT);

        boolean isOwn = com.mctool.mcpatch.core.ApkSignerHelper.V19_CERT_SHA256.equals(fp);
        boolean isExample =
                com.mctool.mcpatch.core.ApkSignerHelper.EXAMPLE_CERT_SHA256.equals(fp);
        assertTrue("指纹应当是已知的两把之一（自己的 or 公开示例的），实际 " + fp,
                isOwn || isExample);

        if (isExample) {
            assertTrue("用公开示例密钥时必须告警，实际:\n" + log, log.contains("示例密钥"));
            assertTrue("界面上也应告警，实际: " + sign, sign.contains("示例密钥"));
        } else {
            assertTrue("用自己的密钥且与改包同签名时，应提示可直接覆盖安装，实际:\n" + log,
                    log.contains("可直接覆盖安装") || log.contains("签名不同"));
        }

        // 解析路径本身必须没问题：PKCS#8 + X.509（不是 KeyStore）。
        // Android 没有 JKS 实现，用 KeyStore 的写法在真机上会抛 JKS not found，
        // 而 Robolectric/JVM 上却是好的 —— 所以这条断言只保证 assets 与解析路径没问题。
        c.pause().stop().destroy();
    }

    @Test
    public void checkboxesDriveEnabledState() {
        ActivityController<MainActivity> c = launch();
        MainActivity a = c.get();

        EditText et = a.findViewById(R.id.etName);
        android.widget.ImageView iv = a.findViewById(R.id.ivSkin);
        CheckBox cbName = a.findViewById(R.id.cbRename);
        CheckBox cbSkin = a.findViewById(R.id.cbSkin);
        CheckBox cbAuto = a.findViewById(R.id.cbAutoExport);

        // 显式设置，避免依赖别的用例留下的偏好状态
        cbName.setChecked(false);
        cbSkin.setChecked(false);
        assertTrue("未勾选时名字输入框应禁用", !et.isEnabled());
        assertTrue("未勾选时皮肤预览应禁用", !iv.isEnabled());

        cbName.setChecked(true);
        cbSkin.setChecked(true);
        assertTrue("勾选后名字输入框应启用", et.isEnabled());
        assertTrue("勾选后皮肤预览应启用", iv.isEnabled());

        // 选文件的按钮不受勾选影响，方便先挑好素材再勾选
        assertTrue("选皮肤按钮应始终可用", a.findViewById(R.id.btnPickSkin).isEnabled());
        assertTrue("选资源包按钮应始终可用", a.findViewById(R.id.btnPickPack).isEnabled());

        assertTrue("默认应选中细手臂", ((RadioButton) a.findViewById(R.id.rbSlim)).isChecked());
        assertTrue("「生成后自动另存」默认应打开", cbAuto.isChecked());
        assertTrue("生成按钮初始应可用", a.findViewById(R.id.btnGenerate).isEnabled());
        assertTrue("安装按钮初始应禁用", !a.findViewById(R.id.btnInstall).isEnabled());
        assertTrue("复制日志按钮应始终可用", a.findViewById(R.id.btnCopyLog).isEnabled());

        // 导入存档：没选文件之前不能点
        assertTrue("未选存档时「导入到游戏」应禁用", !a.findViewById(R.id.btnDoImport).isEnabled());
        assertTrue("「选择存档」按钮应可用", a.findViewById(R.id.btnPickImport).isEnabled());

        c.pause().stop().destroy();
    }

    /** 标题栏右上角的外观切换按钮：菜单项在、且图标能解析出来。 */
    @Test
    public void themeToggleMenuIsWired() {
        ActivityController<MainActivity> c = launch();
        MainActivity a = c.get();

        // 拿一个可用的 Menu 实现来跑 onCreateOptionsMenu
        android.view.Menu menu = new android.widget.PopupMenu(
                a, a.findViewById(R.id.btnGenerate)).getMenu();
        assertTrue("onCreateOptionsMenu 应返回 true", a.onCreateOptionsMenu(menu));

        android.view.MenuItem item = menu.findItem(1);
        assertNotNull("标题栏应有外观切换项", item);
        assertNotNull("外观切换项应有图标（太阳/月亮/跟随）", item.getIcon());
        assertTrue("外观切换项应可点击", item.isEnabled());

        c.pause().stop().destroy();
    }

    /** B 组的核心：上次的选择要能被记住（SharedPreferences）。 */
    @Test
    public void choicesSurviveRestart() {
        ActivityController<MainActivity> c1 = launch();
        MainActivity a1 = c1.get();
        ((CheckBox) a1.findViewById(R.id.cbRename)).setChecked(true);
        ((EditText) a1.findViewById(R.id.etName)).setText("仁渴侯壁rinkehorb");
        ((RadioButton) a1.findViewById(R.id.rbClassic)).setChecked(true);
        ((CheckBox) a1.findViewById(R.id.cbAutoExport)).setChecked(false);
        ((CheckBox) a1.findViewById(R.id.cbPack)).setChecked(true);
        c1.pause().stop().destroy();

        ActivityController<MainActivity> c2 = launch();
        MainActivity a2 = c2.get();
        assertTrue("改名勾选应被记住",
                ((CheckBox) a2.findViewById(R.id.cbRename)).isChecked());
        assertEquals("名字应被记住", "仁渴侯壁rinkehorb",
                ((EditText) a2.findViewById(R.id.etName)).getText().toString());
        assertTrue("手臂选择应被记住",
                ((RadioButton) a2.findViewById(R.id.rbClassic)).isChecked());
        assertTrue("自动另存的开关应被记住",
                !((CheckBox) a2.findViewById(R.id.cbAutoExport)).isChecked());
        assertTrue("资源包勾选应被记住",
                ((CheckBox) a2.findViewById(R.id.cbPack)).isChecked());
        c2.pause().stop().destroy();
    }

    private static boolean assetExists(MainActivity a, String name) {
        try {
            java.io.InputStream in = a.getAssets().open(name);
            in.close();
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
