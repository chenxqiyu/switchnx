import pathlib

KSU = pathlib.Path('/root/nxbuild/kernel-src/drivers/kernelsu')

# 1) 删掉 gcc 6 不认识的 -Wno-gcc-compat
kb = KSU / 'Kbuild'
s = kb.read_text()
n = s.count('-Wno-gcc-compat')
s = s.replace(' -Wno-gcc-compat', '')
kb.write_text(s)
print('Kbuild: removed %d occurrence(s) of -Wno-gcc-compat' % n)

# 2) apk_sign.c 补 kvmalloc/kvfree 兼容（4.9 没有，4.12 才引入）
f = KSU / 'manager' / 'apk_sign.c'
s = f.read_text()
if 'ksu_apk_kvmalloc_shim' not in s:
    shim = '''/* 4.9 \u6ca1\u6709 kvmalloc/kvfree\uff084.12 \u624d\u5f15\u5165\uff09\uff0c\u8fd9\u91cc\u63d0\u4f9b\u7b49\u4ef7\u5b9e\u73b0 */
#define ksu_apk_kvmalloc_shim
#ifndef kvmalloc
#include <linux/vmalloc.h>
static inline void *kvmalloc(size_t size, gfp_t flags)
{
	void *buf = kmalloc(size, flags);
	if (!buf)
		buf = vmalloc(size);
	return buf;
}
static inline void kvfree(const void *buf)
{
	if (is_vmalloc_addr(buf))
		vfree(buf);
	else
		kfree(buf);
}
#endif

'''
    # 插到第一个 #include 之后
    idx = s.find('#include "util.h"')
    if idx < 0:
        idx = s.find('#include')
    s = s[:idx] + shim + s[idx:]
    f.write_text(s)
    print('apk_sign.c: kvmalloc shim inserted')
else:
    print('apk_sign.c: already patched')

print('\n--- apk_sign.c head ---')
print('\n'.join(f.read_text().splitlines()[:16]))
