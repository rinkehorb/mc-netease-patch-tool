import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;

/**
 * 按【像素】比较两张 PNG —— 用来核对改包后的皮肤图是否就是给的那张。
 *
 * <p>为什么不比字节：工具写 PNG 时会走一次 Bitmap 编码，字节数会变
 * （实测 1937 → 3165），但像素可以完全一样。比字节会误报"没生效"。
 *
 * 用法: java ComparePng &lt;期望.png&gt; &lt;实际.png&gt;
 */
public final class ComparePng {
    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("用法: ComparePng <期望.png> <实际.png>");
            System.exit(2);
        }
        BufferedImage a = ImageIO.read(new File(args[0]));
        BufferedImage b = ImageIO.read(new File(args[1]));
        if (a == null || b == null) {
            System.out.println("  读不了图片（a=" + a + ", b=" + b + "）");
            return;
        }
        System.out.printf("  期望: %dx%d   实际: %dx%d%n", a.getWidth(), a.getHeight(), b.getWidth(), b.getHeight());
        if (a.getWidth() != b.getWidth() || a.getHeight() != b.getHeight()) {
            System.out.println("  尺寸不同 → ✗");
            return;
        }
        int diff = 0, total = a.getWidth() * a.getHeight();
        for (int y = 0; y < a.getHeight(); y++) {
            for (int x = 0; x < a.getWidth(); x++) {
                if (a.getRGB(x, y) != b.getRGB(x, y)) diff++;
            }
        }
        System.out.printf("  像素总数 %d，不同 %d%n", total, diff);
        System.out.println(diff == 0 ? "  → 像素完全一致 ✔（皮肤确实换成了这张）"
                                     : "  → 有 " + diff + " 个像素不同 ✗");
    }
}
