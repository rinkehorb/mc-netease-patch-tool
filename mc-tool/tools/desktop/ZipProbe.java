import java.io.File;
import java.util.Enumeration;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** 只做一件事：用 Java 自己的 java.util.zip.ZipFile 打开给定的 APK，报告能不能读、多少条。 */
public class ZipProbe {
    public static void main(String[] args) {
        for (String p : args) {
            File f = new File(p);
            System.out.print("  " + f.getName() + " (" + f.length() + " 字节): ");
            try (ZipFile z = new ZipFile(f)) {
                int n = 0;
                for (Enumeration<? extends ZipEntry> e = z.entries(); e.hasMoreElements(); e.nextElement()) {
                    n++;
                }
                System.out.println("Java 能读， " + n + " 条");
            } catch (Throwable t) {
                System.out.println("Java 读不了 → " + t);
            }
        }
    }
}
