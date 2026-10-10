package com.mctool.mcpatch;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 「免 root 换手臂粗细」——把一份改好的 {@code options.txt} 打成包，交给
 * {@link ShareWriter} 写成 {@code Download/mcarm_3px.png} / {@code mcarm_4px.png}。
 *
 * <h3>为什么这条路能成立（2026-10-10 在真机上打通）</h3>
 * 手臂体型存在 {@code /data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe/options.txt}
 * 的 {@code game_skintypefull} 那一行：
 * <pre>
 *   game_skintypefull:Standard_Alex   → 细手臂 3px
 *   game_skintypefull:Standard_Steve  → 粗手臂 4px
 * </pre>
 * 那个文件在游戏<b>自己的私有目录</b>里 —— 普通应用（包括 Shizuku）碰不到，但
 * <b>游戏自己能写</b>。而游戏里的 H5 有一条
 * {@code h5adaptor.decompress_map(源zip, 目标目录, true)}，以<b>游戏身份</b>解压写入，
 * 于是可以让游戏自己覆盖自己的配置。
 *
 * <p>实测证据：一加（有 root）先用 root 逐字节确认覆盖成功；
 * vivo（<b>无 root</b>）走完整流程后重启游戏，手臂真的从 3px 变成 4px。
 *
 * <h3>代价（必须在界面上说清楚）</h3>
 * H5 <b>没有读文本文件的接口</b>（只有读图片的 {@code get_local_image_by_item_id}），
 * 所以只能<b>整份覆盖</b> {@code options.txt} —— 用户的其他设置
 * （画质 / 视野 / 控制 / 语言…）会回到模板里的值。
 * 换句话说：这个功能 = 「重置设置 + 顺手把手臂切成你要的粗细」。
 *
 * <h3>为什么用两个文件名</h3>
 * H5 那侧读不到文件内容（没有读接口），所以用它<b>能看见的东西</b>——
 * 文件名——来区分：{@code mcarm_3px.png} / {@code mcarm_4px.png}。
 * 文件内容里本来就已经是对应粗细的 {@code options.txt}。
 *
 * <p>另外：{@code decompress_map} <b>成功后会吃掉源文件</b>，所以同一个包天然只能生效一次，
 * 不需要任何状态记录。
 */
public final class ArmSwitch {

    /** 3px（细手臂，Alex 体型）的包名（不含 {@code .png}）。 */
    public static final String BASE_3PX = "mcarm_3px";
    /** 4px（粗手臂，Steve 体型）的包名（不含 {@code .png}）。 */
    public static final String BASE_4PX = "mcarm_4px";

    private static final String ASSET_3PX = "options-arm3.txt";
    private static final String ASSET_4PX = "options-arm4.txt";

    /** 游戏侧要写进去的目录（qihoo 渠道包，路径固定）。 */
    public static final String DEST_DIR =
            "/data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe";

    private ArmSwitch() {
    }

    public static String baseName(boolean slim) {
        return slim ? BASE_3PX : BASE_4PX;
    }

    public static String assetName(boolean slim) {
        return slim ? ASSET_3PX : ASSET_4PX;
    }

    /** 界面上的说法：true=细手臂 3px。 */
    public static String label(boolean slim) {
        return slim ? "3px 细手臂（Alex）" : "4px 粗手臂（Steve）";
    }

    /**
     * 读 assets 里的模板，打成一个<b>只含 {@code options.txt}</b> 的 zip。
     *
     * <p>只放一个文件、而且放在根目录，是因为 {@code decompress_map} 会把包内
     * 目录结构<b>完全压平</b>（见 9 节的实测），目标目录直接指向
     * {@code .../minecraftpe} 即可。
     */
    public static byte[] buildZip(Context ctx, boolean slim) throws IOException {
        byte[] raw = readAsset(ctx, assetName(slim));
        ByteArrayOutputStream bos = new ByteArrayOutputStream(raw.length + 512);
        ZipOutputStream zos = new ZipOutputStream(bos);
        try {
            ZipEntry e = new ZipEntry("options.txt");
            zos.putNextEntry(e);
            zos.write(raw);
            zos.closeEntry();
            zos.finish();
        } finally {
            zos.close();
        }
        return bos.toByteArray();
    }

    /** 只用于自检/测试：模板里那一行到底是什么。 */
    public static String armLine(Context ctx, boolean slim) throws IOException {
        String s = new String(readAsset(ctx, assetName(slim)), "UTF-8");
        for (String line : s.split("\n")) {
            if (line.startsWith("game_skintypefull:")) return line.trim();
        }
        return "(找不到 game_skintypefull)";
    }

    private static byte[] readAsset(Context ctx, String name) throws IOException {
        InputStream is = ctx.getAssets().open(name);
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream(8192);
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
            return bos.toByteArray();
        } finally {
            try {
                is.close();
            } catch (IOException ignored) {
            }
        }
    }
}
