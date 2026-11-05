import pathlib

f = pathlib.Path('/root/nxbuild/kernel-src/drivers/kernelsu/policy/allowlist.c')
s = f.read_text()

# 1) kernel_write 第二参加强转，兼容 4.9 的 const void * 严格检查
n1 = s.count('kernel_write(fp, &')
s = s.replace('kernel_write(fp, &', 'kernel_write(fp, (const void *)&')
print('kernel_write casts: %d' % n1)

# 2) strscpy_pad(4.14+) 垫片：先清零再 strscpy
if 'ksu_strscpy_pad_shim' not in s:
    shim = (
        '\n/* 4.14+ \u624d\u6709 strscpy_pad\uff0c4.9 \u7528 memset+strscpy \u7b49\u4ef7\u5b9e\u73b0 */\n'
        '#define ksu_strscpy_pad_shim\n'
        '#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 14, 0)\n'
        '#ifndef strscpy_pad\n'
        'static inline ssize_t strscpy_pad(char *dest, const char *src, size_t count)\n'
        '{\n'
        '\tsize_t len;\n'
        '\tssize_t ret = strscpy(dest, src, count);\n'
        '\tif (ret < 0)\n'
        '\t\treturn ret;\n'
        '\tlen = (size_t)ret;\n'
        '\tif (len < count)\n'
        '\t\tmemset(dest + len, 0, count - len);\n'
        '\treturn ret;\n'
        '}\n'
        '#endif\n'
        '#endif\n'
    )
    # 插到最后一个 #include 之后
    lines = s.splitlines(True)
    last = 0
    for i, ln in enumerate(lines[:40]):
        if ln.lstrip().startswith('#include'):
            last = i
    lines.insert(last + 1, shim)
    s = ''.join(lines)
    print('strscpy_pad shim inserted after line %d' % (last + 1))

f.write_text(s)

print('\n--- head 24 ---')
print('\n'.join(f.read_text().splitlines()[:24]))
