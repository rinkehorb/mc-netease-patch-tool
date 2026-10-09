package com.mctool.mcpatch.core;

import java.io.BufferedOutputStream;
import java.io.Closeable;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.CRC32;
import java.util.zip.Deflater;

/**
 * 手写的 ZIP 写入器（纯 Java，无 Android 依赖）。
 *
 * <p>为什么不用 {@link java.util.zip.ZipOutputStream}：
 * <ol>
 *   <li>未压缩（STORED）条目需要做 zipalign 等价的 <b>4 字节对齐</b>，
 *       靠的是往 local header 里塞 padding extra field，ZipOutputStream 做不到；</li>
 *   <li>需要把源 APK 里的 STORED 条目<b>原样搬运</b>（直接沿用源包的 CRC/大小），
 *       ZipOutputStream 只能重新压缩；</li>
 *   <li>需要精确控制压缩方式，避免触碰 Android 对 resources.arsc / lib/*.so 的对齐要求。</li>
 * </ol>
 *
 * <p>DEFLATED 条目采用「bit3 + data descriptor」的流式写法：
 * 头部先写 0，压缩完再补一个 descriptor。这样不需要事先知道
 * CRC 和压缩后大小，常驻内存与文件大小无关（手机的 165 MB 包也能跑）。
 * 源 APK 自己给 classes.dex 用的就是这个写法，兼容性没有问题。
 */
public final class RawZipWriter implements Closeable {

    /** 与 zipalign 一致的 padding extra field id。 */
    private static final int EXTRA_ID = 0xD935;
    private static final int ALIGN = 4;
    private static final int BUFFER = 1 << 16;

    private static final byte[] NO_EXTRA = new byte[0];

    private static final class Cd {
        byte[] name;
        int flags;
        int method;
        int dosTime;
        int dosDate;
        long crc;
        long csize;
        long usize;
        byte[] extra;
        long localHeaderOffset;
    }

    private final OutputStream out;
    private final List<Cd> cds = new ArrayList<Cd>();
    private long offset;
    private boolean finished;

    public RawZipWriter(File target) throws IOException {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("无法创建目录: " + parent);
        }
        this.out = new BufferedOutputStream(new FileOutputStream(target), 1 << 20);
    }

    // ------------------------------------------------------------------ 对外接口

    /**
     * 写入一个 STORED（不压缩）条目，CRC 与长度由调用方给出（搬运源包条目时直接沿用源值）。
     */
    public void addStored(String name, long crc, long size, InputStream data) throws IOException {
        if (finished) throw new IllegalStateException("already finished");
        byte[] nameB = name.getBytes(StandardCharsets.UTF_8);
        long lho = offset;

        long base = offset + 30L + nameB.length;
        int pad = (int) ((ALIGN - (base % ALIGN)) % ALIGN);
        byte[] extra = NO_EXTRA;
        if (pad != 0) {
            // extra field 至少要 4 字节头部，所以 1..3 时补成 pad+4（mod 4 不变）
            int len = pad < 4 ? pad + 4 : pad;
            extra = new byte[len];
            put16(extra, 0, EXTRA_ID);
            put16(extra, 2, len - 4);
        }

        int tm = dosTimeOf(System.currentTimeMillis());
        int dt = dosDateOf(System.currentTimeMillis());

        byte[] lh = new byte[30];
        put32(lh, 0, 0x04034b50L);
        put16(lh, 4, 20);          // version needed to extract
        put16(lh, 6, 0x0800);      // general purpose flag: UTF-8 文件名
        put16(lh, 8, 0);           // method = STORED
        put16(lh, 10, tm);
        put16(lh, 12, dt);
        put32(lh, 14, crc);
        put32(lh, 18, size);
        put32(lh, 22, size);
        put16(lh, 26, nameB.length);
        put16(lh, 28, extra.length);
        write(lh);
        write(nameB);
        write(extra);

        long written = pipe(data, size);
        if (written != size) {
            throw new IOException("STORED 条目 " + name + " 实际写入 " + written + " 字节，与声明的 " + size + " 不符");
        }

        Cd cd = new Cd();
        cd.name = nameB;
        cd.flags = 0x0800;
        cd.method = 0;
        cd.dosTime = tm;
        cd.dosDate = dt;
        cd.crc = crc;
        cd.csize = size;
        cd.usize = size;
        cd.extra = extra;
        cd.localHeaderOffset = lho;
        cds.add(cd);
    }

    /** 写入一个小条目并做 DEFLATE 压缩。 */
    public void addDeflated(String name, byte[] data) throws IOException {
        addDeflated(name, new java.io.ByteArrayInputStream(data));
    }

    /** 流式写入一个 DEFLATE 条目（bit3 + data descriptor，常驻内存恒定）。 */
    public void addDeflated(String name, InputStream data) throws IOException {
        if (finished) throw new IllegalStateException("already finished");
        byte[] nameB = name.getBytes(StandardCharsets.UTF_8);
        long lho = offset;

        int tm = dosTimeOf(System.currentTimeMillis());
        int dt = dosDateOf(System.currentTimeMillis());

        byte[] lh = new byte[30];
        put32(lh, 0, 0x04034b50L);
        put16(lh, 4, 20);
        put16(lh, 6, 0x0800 | 0x0008);   // UTF-8 名字 + 有 data descriptor
        put16(lh, 8, 8);                 // method = DEFLATE
        put16(lh, 10, tm);
        put16(lh, 12, dt);
        put32(lh, 14, 0);                // crc 未知
        put32(lh, 18, 0);                // csize 未知
        put32(lh, 22, 0);                // usize 未知
        put16(lh, 26, nameB.length);
        put16(lh, 28, 0);
        write(lh);
        write(nameB);

        Deflater def = new Deflater(Deflater.DEFAULT_COMPRESSION, true /* raw deflate */);
        CRC32 crc = new CRC32();
        long usize = 0, csize = 0;
        byte[] inBuf = new byte[BUFFER];
        byte[] outBuf = new byte[BUFFER];
        try {
            int n;
            while ((n = data.read(inBuf)) > 0) {
                crc.update(inBuf, 0, n);
                usize += n;
                def.setInput(inBuf, 0, n);
                while (!def.needsInput()) {
                    int k = def.deflate(outBuf);
                    if (k > 0) {
                        write(outBuf, 0, k);
                        csize += k;
                    } else {
                        break;
                    }
                }
            }
            def.finish();
            while (!def.finished()) {
                int k = def.deflate(outBuf);
                if (k > 0) {
                    write(outBuf, 0, k);
                    csize += k;
                } else {
                    break;  // 防御：避免极端情况下死循环
                }
            }
        } finally {
            def.end();
        }

        byte[] dd = new byte[16];
        put32(dd, 0, 0x08074b50L);       // data descriptor signature
        put32(dd, 4, crc.getValue());
        put32(dd, 8, csize);
        put32(dd, 12, usize);
        write(dd);

        Cd cd = new Cd();
        cd.name = nameB;
        cd.flags = 0x0800 | 0x0008;
        cd.method = 8;
        cd.dosTime = tm;
        cd.dosDate = dt;
        cd.crc = crc.getValue();
        cd.csize = csize;
        cd.usize = usize;
        cd.extra = NO_EXTRA;
        cd.localHeaderOffset = lho;
        cds.add(cd);
    }

    @Override
    public void close() throws IOException {
        finish();
    }

    public void finish() throws IOException {
        if (finished) return;
        finished = true;

        long cdStart = offset;
        for (Cd c : cds) {
            byte[] rec = new byte[46];
            put32(rec, 0, 0x02014b50L);
            put16(rec, 4, 20);              // version made by
            put16(rec, 6, 20);              // version needed
            put16(rec, 8, c.flags);
            put16(rec, 10, c.method);
            put16(rec, 12, c.dosTime);
            put16(rec, 14, c.dosDate);
            put32(rec, 16, c.crc);
            put32(rec, 20, c.csize);
            put32(rec, 24, c.usize);
            put16(rec, 28, c.name.length);
            put16(rec, 30, c.extra.length);
            put16(rec, 32, 0);              // file comment length
            put16(rec, 34, 0);              // disk number start
            put16(rec, 36, 0);              // internal attributes
            put32(rec, 38, 0);              // external attributes
            put32(rec, 42, c.localHeaderOffset);
            write(rec);
            write(c.name);
            write(c.extra);
        }
        long cdSize = offset - cdStart;

        byte[] eocd = new byte[22];
        put32(eocd, 0, 0x06054b50L);
        put16(eocd, 4, 0);
        put16(eocd, 6, 0);
        put16(eocd, 8, cds.size());
        put16(eocd, 10, cds.size());
        put32(eocd, 12, cdSize);
        put32(eocd, 16, cdStart);
        put16(eocd, 20, 0);
        write(eocd);

        out.flush();
        out.close();
    }

    public int entryCount() {
        return cds.size();
    }

    // ------------------------------------------------------------------ 内部

    private long pipe(InputStream in, long size) throws IOException {
        byte[] buf = new byte[BUFFER];
        long total = 0;
        int n;
        while ((n = in.read(buf)) > 0) {
            out.write(buf, 0, n);
            total += n;
            offset += n;
        }
        return total;
    }

    private void write(byte[] b) throws IOException {
        out.write(b);
        offset += b.length;
    }

    private void write(byte[] b, int off, int len) throws IOException {
        out.write(b, off, len);
        offset += len;
    }

    private static void put16(byte[] b, int off, int v) {
        b[off] = (byte) (v & 0xFF);
        b[off + 1] = (byte) ((v >>> 8) & 0xFF);
    }

    private static void put32(byte[] b, int off, long v) {
        b[off] = (byte) (v & 0xFF);
        b[off + 1] = (byte) ((v >>> 8) & 0xFF);
        b[off + 2] = (byte) ((v >>> 16) & 0xFF);
        b[off + 3] = (byte) ((v >>> 24) & 0xFF);
    }

    private static int dosTimeOf(long millis) {
        java.util.Calendar c = java.util.Calendar.getInstance();
        c.setTimeInMillis(millis);
        return (c.get(java.util.Calendar.HOUR_OF_DAY) << 11)
                | (c.get(java.util.Calendar.MINUTE) << 5)
                | (c.get(java.util.Calendar.SECOND) / 2);
    }

    private static int dosDateOf(long millis) {
        java.util.Calendar c = java.util.Calendar.getInstance();
        c.setTimeInMillis(millis);
        int year = c.get(java.util.Calendar.YEAR);
        if (year < 1980) year = 1980;
        return ((year - 1980) << 9)
                | ((c.get(java.util.Calendar.MONTH) + 1) << 5)
                | c.get(java.util.Calendar.DAY_OF_MONTH);
    }
}
