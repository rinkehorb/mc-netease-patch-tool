package com.mctool.mcpatch;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;

/**
 * 把「导入包」写到公共的 {@code Download/} 目录。
 *
 * <h3>为什么必须写到公共目录</h3>
 * 这些包是给<b>另一个应用</b>（《我的世界》）读的：游戏里的 H5 会直接按
 * {@code /sdcard/Download/mcweb_1_root.zip} 这样的绝对路径去打开它们。
 * 所以不能放在本应用的 {@code Android/data} 里（游戏读不到）。
 *
 * <h3>不需要任何权限</h3>
 * Android 10+ 走 {@link MediaStore.Downloads}，往公共 Download 集合写自己的文件
 * 是**不需要权限**的；Android 9 及以下退回直接文件路径，那时需要在
 * manifest 里声明 {@code WRITE_EXTERNAL_STORAGE}（已带 {@code maxSdkVersion="28"}）。
 */
public final class DownloadWriter {

    private DownloadWriter() {
    }

    /** 覆盖写入 {@code Download/<name>}，返回可读的 Uri（API 29+）或 null（旧系统）。 */
    public static Uri write(Context ctx, String name, byte[] data, String mime)
            throws IOException {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return writeViaMediaStore(ctx, name, data, mime);
        }
        File f = new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), name);
        FileOutputStream os = new FileOutputStream(f);
        try {
            os.write(data);
        } finally {
            os.close();
        }
        return null;
    }

    /**
     * {@code Download/<name>} 是否已经存在。
     *
     * <p>用来挑「空闲槽位」：游戏把包解压掉之后源文件会被消耗，那个槽位就又空出来了，
     * 所以这个判断天然等价于「这个槽位还没被导入过」。
     */
    public static boolean exists(Context ctx, String name) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            android.database.Cursor c = null;
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
        File f = new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), name);
        return f.exists();
    }

    private static Uri writeViaMediaStore(Context ctx, String name, byte[] data, String mime)
            throws IOException {
        ContentResolver cr = ctx.getContentResolver();
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;

        // 先删掉同名旧文件（可能残留自上一次导入，或上次没被游戏消耗掉）
        try {
            cr.delete(collection, MediaStore.MediaColumns.DISPLAY_NAME + "=?",
                    new String[]{name});
        } catch (Throwable ignored) {
        }

        ContentValues v = new ContentValues();
        v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
        v.put(MediaStore.MediaColumns.MIME_TYPE, mime == null ? "application/zip" : mime);
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
        ContentValues done = new ContentValues();
        done.put(MediaStore.MediaColumns.IS_PENDING, 0);
        try {
            cr.update(uri, done, null, null);
        } catch (Throwable ignored) {
        }
        return uri;
    }
}
