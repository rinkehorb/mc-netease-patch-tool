# 这两个文件是给「改出来的游戏包」签名用的

| 文件 | 是什么 | 进仓库吗 |
|---|---|---|
| `mc-patch-key.pk8.example` | **公用示例密钥**的私钥（PKCS#8 未加密 DER） | ✅ 进（故意公开，方便开箱即用） |
| `mc-patch-cert.pem.example` | 对应的自签 X.509 证书 | ✅ 进 |
| `mc-patch-key.pk8` | 你**实际使用**的私钥 | ❌ 不进（`.gitignore` 排除） |
| `mc-patch-cert.pem` | 对应的证书 | ❌ 不进 |

**真正被读取的是不带 `.example` 的那两个。** 第一次构建前先生成：

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File tools\genkey.ps1
```
```bash
# Linux / macOS
./tools/genkey.sh
```

想偷懒直接用公开的示例密钥（谁都能覆盖安装你的包，自己评估）：

```powershell
powershell -ExecutionPolicy Bypass -File tools\genkey.ps1 -UseExampleKey
```

## 为什么不能走 KeyStore

Android 支持的 KeyStore 类型只有 BKS / PKCS12 / AndroidKeyStore —— **JKS 是 JDK 专有格式**，
真机上 `KeyStore.getInstance("JKS")` 直接抛 `KeyStoreException: JKS not found`。
所以这里刻意把签名材料**导出成两个不依赖任何 KeyStore provider 的文件**：
读取时只需要 `KeyFactory.getInstance("RSA")` 和 `CertificateFactory.getInstance("X.509")`，
这两个在 Android 和桌面 JVM 上都一定存在。

（工具 APK 自己的签名走的是 Gradle/`app/keystore/mc-patch.jks`，那是**另一回事**，
构建期在桌面 JVM 上跑，用 JKS 没问题。见 `app/keystore/README.md`。）

## ⚠️ 换密钥的代价

**一旦你用某个密钥装过改包，以后就必须一直用同一个密钥**，否则系统会拒绝覆盖安装，
只能卸载重装 —— 而**卸载会删掉 `Android/data/`，你的存档就全没了**。
所以：先想清楚，再动手；并且把这两个文件另外备份一份。
