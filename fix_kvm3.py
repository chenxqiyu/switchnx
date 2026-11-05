import pathlib
import re

f = pathlib.Path('/root/nxbuild/kernel-src/drivers/kernelsu/manager/apk_sign.c')
s = f.read_text()

# 用版本判断替换整块垫片：4.9 已有 kvfree，只缺 kvmalloc(4.12+)
new = (
    '\n/* 4.9 \u5df2\u6709 kvfree\uff0c\u53ea\u6709 kvmalloc \u662f 4.12 \u624d\u52a0\u7684 */\n'
    '#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 12, 0)\n'
    '#include <linux/mm.h>\n'
    '#include <linux/vmalloc.h>\n'
    '#ifndef kvmalloc\n'
    'static inline void *kvmalloc(size_t size, gfp_t flags)\n'
    '{\n'
    '\tvoid *buf = kmalloc(size, flags);\n'
    '\tif (!buf)\n'
    '\t\tbuf = vmalloc(size);\n'
    '\treturn buf;\n'
    '}\n'
    '#endif\n'
    '#endif\n'
)

s = re.sub(
    r'\n/\* 4\.9 \u6ca1\u6709 kvmalloc[^\n]*\*/\n#ifndef kvmalloc\n.*?\n#endif\n\n',
    '\n', s, count=1, flags=re.S)

anchor = '#include <linux/version.h>'
s = s.replace(anchor, anchor + '\n' + new, 1)
f.write_text(s)

print('--- head 26 lines ---')
print('\n'.join(f.read_text().splitlines()[:26]))
