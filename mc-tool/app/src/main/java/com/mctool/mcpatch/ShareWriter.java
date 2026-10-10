package com.mctool.mcpatch;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;

/**
 * 把「导入包」写到一个<b>游戏真的读得到</b>的位置。
 *
 * <h3>为什么后缀是 {@code .png}（这是整个类存在的全部原因，别改成 .zip）</h3>
 * 这条路上踩了三次，最后才搞清楚 Android 的真实规则：
 *
 * <ol>
 *   <li><b>放 {@code Download/}，后缀 {@code .zip}</b> —— 真机报
 *       {@code [Errno 13] Permission denied}。原因不是路径，而是<b>归属</b>：
 *       {@code /sdcard} 上由某个 App 创建的文件是 {@code -rwxrwx--- owner:media_rw}，
 *       "other" 没有任何权限位，而且 {@code chmod} 在这层是<b>虚拟的</b>、改不动。</li>
 *   <li><b>改放 {@code Android/media/<包名>/}</b>（Android 官方说的"跨 App 共享"位置）——
 *       在 Android 13 上确实能读（实测通过），但在 <b>Android 15</b> 上照样
 *       {@code Errno 13}。而且实测确认：游戏 {@code READ_EXTERNAL_STORAGE} 已授予、
 *       {@code targetSdk} 才 22，<b>权限完全不是原因</b>。</li>
 *   <li>⇒ 真正的规则（Android 11+ 的分区存储）：别的 App 创建的
 *       <b>非媒体文件</b>（{@code .zip} / {@code .json} / {@code .txt} 这些）
 *       <b>任何位置、任何权限都读不到</b>；而 <b>媒体文件</b>（图片 / 音频 / 视频）
 *       只要有 {@code READ_EXTERNAL_STORAGE} / {@code READ_MEDIA_*} 就能<b>按路径读</b>。
 *       这正是音乐播放器、相册还能按路径扫全盘的原因。</li>
 * </ol>
 *
 * <b>所以：用 MediaStore 把包登记成图片（后缀 {@code .png}、MIME {@code image/png}），
 * 游戏就能按路径打开它。</b> 文件内容仍然是标准 zip —— {@code decompress_map}
 * 只把它当 zip 解，不看后缀（Python 的 {@code zipfile} 也不看）。
 *
 * <p>路径形如 {@code /sdcard/Download/mcweb_1_root.png}；
 * 游戏侧的候选列表在 {@code assets/mc-import.js} 的 {@code CANDS}。
 *
 * <h3>权限</h3>
 * Android 10+ 走 MediaStore 写自己的文件，<b>不需要任何权限</b>；
 * 9 及以下退回文件路径，需要 manifest 里那个
 * {@code WRITE_EXTERNAL_STORAGE}（已带 {@code maxSdkVersion="28"}）。
 */
public final class ShareWriter {

    /** 包名硬编码在这里，因为游戏侧要用它拼路径 —— 改包名必须同步改 mc-import.js。 */
    public static final String PKG = "com.mctool.mcpatch";

    /** 伪装成图片的后缀。**不要改成 .zip**，见类注释。 */
    public static final String EXT = ".png";

    /** 对应的 MIME，必须和 EXT 一致，否则 MediaStore 不会当媒体文件登记。 */
    private static final String MIME = "image/png";

    private ShareWriter() {
    }

    /** 给日志用的一行位置描述。 */
    public static String dirDesc() {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                + "/  （伪装成图片 " + EXT + " / " + MIME + "，游戏才读得到）";
    }

    /** 覆盖写入一个包，返回它的绝对路径。 */
    public static File write(Context ctx, String baseName, byte[] data) throws IOException {
        String name = baseName + EXT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            writeViaMediaStore(ctx, name, data);
        } else {
            File f = new File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), name);
            FileOutputStream os = new FileOutputStream(f);
            try {
                os.write(data);
                os.flush();
            } finally {
                os.close();
            }
        }
        return new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), name);
    }

    /** 这个槽位是不是还有没被游戏消耗掉的包（用来挑空闲槽位）。 */
    public static boolean exists(Context ctx, String baseName) {
        return exists(ctx, baseName, EXT);
    }

    /** 去掉扩展名的文件名（用于匹配 MediaStore 自动加的 " (1)" 后缀）。 */
    private static String stemOf(String name) {
        int i = name.lastIndexOf('.');
        return i > 0 ? name.substring(0, i) : name;
    }

    /**
     * 清掉 Download 里所有 mcweb_* 残留（所有槽位，含 MediaStore 自动加的 (N) 后缀）。
     *
     * <p>为什么必须清"所有"而不是只清当前槽位：游戏侧的 H5 是从槽位 1 依次扫的，
     * 只要前面留着一个"半截"的槽位（比如只有 _db 没有 _root），它就会卡在那一格，
     * 后面的完整包永远轮不到 —— 真机现象就是"怎么点都导入不了"。
     * 实测：18:40 的残缺 mcweb_4_* 挡住了 18:44 完整的 mcweb_5_*。
     *
     * @return 删掉的条数
     */
    public static int purgeAll(Context ctx) {
        int n = 0;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                n = ctx.getContentResolver().delete(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                        MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                        new String[]{"mcweb_%"});
            } catch (Throwable ignored) {
            }
        }
        try {
            File dir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS);
            File[] fs = dir.listFiles();
            if (fs != null) {
                for (File f : fs) {
                    if (f.getName().startsWith("mcweb_")) {
                        if (f.delete()) n++;
                    }
                }
            }
        } catch (Throwable ignored) {
        }
        return n;
    }

    /**
     * 清掉某个槽位在 Download 里的<b>全部</b>残留。
     *
     * <p>{@code LIKE 'mcweb_<slot>_%'} 会把 {@code mcweb_1_db.png} 和
     * MediaStore 自动改名出来的 {@code mcweb_1_db (1).png} 一起带走。
     *
     * <p>为什么必须清：工具每次都写同一个名字，若旧行没删干净，MediaStore 就改名，
     * 于是 Download 堆一堆同名文件，游戏扫候选时可能挑到早被消耗的旧包 →
     * 「找到了包但打不开 / 权限不足」。真机实测：连点几次后堆了 26 个，第一次点必失败。
     *
     * @return 删掉的条数
     */
    public static int purgeSlot(Context ctx, int slot) {
        String prefix = "mcweb_" + slot + "_";
        int n = 0;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                n = ctx.getContentResolver().delete(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                        MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                        new String[]{prefix + "%"});
            } catch (Throwable ignored) {
            }
        }
        try {
            File dir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS);
            File[] fs = dir.listFiles();
            if (fs != null) {
                for (File f : fs) {
                    if (f.getName().startsWith(prefix)) {
                        if (f.delete()) n++;
                    }
                }
            }
        } catch (Throwable ignored) {
        }
        return n;
    }

    /**
     * 删掉同名的包（{@code .png} 和旧版留下的 {@code .zip} 都删）。
     *
     * <p>用于「换手臂粗细」：那两个包（{@code mcarm_3px} / {@code mcarm_4px}）
     * 必须保证<b>同一时刻只有一个</b>，否则游戏先找到哪个就用哪个，
     * 用户后点的那个等于白点。被游戏消耗过的包本来就不存在，删是安全的。
     */
    public static void delete(Context ctx, String baseName) {
        for (String ext : new String[]{EXT, ".zip"}) {
            String name = baseName + ext;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                try {
                    ctx.getContentResolver().delete(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                            MediaStore.MediaColumns.DISPLAY_NAME + "=?",
                            new String[]{name});
                } catch (Throwable ignored) {
                }
            }
            try {
                File f = new File(Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS), name);
                if (f.exists()) {
                    //noinspection ResultOfMethodCallIgnored
                    f.delete();
                }
            } catch (Throwable ignored) {
            }
        }
    }

    /** 也查一下旧版留下的 {@code .zip}，免得槽位判断把旧文件当成"空的"。 */
    public static boolean existsAny(Context ctx, String baseName) {
        return exists(ctx, baseName, EXT) || exists(ctx, baseName, ".zip");
    }

    private static boolean exists(Context ctx, String baseName, String ext) {
        String name = baseName + ext;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            Cursor c = null;
            try {
                c = ctx.getContentResolver().query(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                        new String[]{MediaStore.MediaColumns._ID},
                        MediaStore.MediaColumns.DISPLAY_NAME + "=? AND "
                                + MediaStore.MediaColumns.RELATIVE_PATH + " LIKE ?",
                        new String[]{name, Environment.DIRECTORY_DOWNLOADS + "%"},
                        null);
                return c != null && c.moveToFirst();
            } catch (Throwable e) {
                return false;
            } finally {
                if (c != null) {
                    try {
                        c.close();
                    } catch (Throwable ignored) {
                    }
                }
            }
        }
        return new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), name).exists();
    }

    private static void writeViaMediaStore(Context ctx, String name, byte[] data)
            throws IOException {
        ContentResolver cr = ctx.getContentResolver();
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;

        // 先删同名旧文件（可能残留自上一次导入，或上次没被游戏消耗掉）。
        // ⚠️ 必须连 " (1)" " (2)" 这类【MediaStore 自动改名的残留】一起删：
        // 否则每次写都会多出一个新名字的文件，Download 里越堆越多，
        // 游戏扫 mcweb_<slot>_* 时可能挑到早已被消耗掉的旧包
        // —— 真机上就是「找到了包，但游戏打不开 / 权限不足」（实测堆过 26 个）。
        try {
            cr.delete(collection,
                    MediaStore.MediaColumns.DISPLAY_NAME + "=? OR "
                            + MediaStore.MediaColumns.DISPLAY_NAME + " LIKE ?",
                    new String[]{name, stemOf(name) + " (%"});
        } catch (Throwable ignored) {
        }

        ContentValues v = new ContentValues();
        v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
        v.put(MediaStore.MediaColumns.MIME_TYPE, MIME);
        v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
        v.put(MediaStore.MediaColumns.IS_PENDING, 1);

        Uri uri = cr.insert(collection, v);
        if (uri == null) throw new IOException("MediaStore 插入失败: " + name);
        OutputStream os = null;
        try {
            os = cr.openOutputStream(uri, "w");
            if (os == null) throw new IOException("打不开输出流: " + name);
            os.write(data);
            os.flush();
        } finally {
            if (os != null) {
                try {
                    os.close();
                } catch (IOException ignored) {
                }
            }
        }
        // 关键：清掉 IS_PENDING，别的 App 才看得到这个文件
        ContentValues done = new ContentValues();
        done.put(MediaStore.MediaColumns.IS_PENDING, 0);
        try {
            cr.update(uri, done, null, null);
        } catch (Throwable ignored) {
        }
    }
}
