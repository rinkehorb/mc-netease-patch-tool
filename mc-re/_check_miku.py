from PIL import Image
img = Image.open(r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png')
print('尺寸:', img.size, '模式:', img.mode)
# MC 皮肤标准尺寸：64x32（旧）或 64x64（新）
print('标准 MC 皮肤应为 64x32 或 64x64')
