import pathlib
import re

f = pathlib.Path('/root/nxbuild/kernel-src/drivers/kernelsu/manager/apk_sign.c')
s = f.read_text()

# 删掉之前插在文件头的错误垫片
s = re.sub(
    r'/\* 4\.9 [^\n]*\*/\n#define ksu_apk_kvmalloc_shim\n#ifndef kvmalloc\n.*?#endif\n\n',
    '', s, count=1, flags=re.S)

SHIM = (
    '\n/* 4.9 \u6ca1\u6709 kvmalloc/kvfree\uff084.12 \u624d\u5f15\u5165\uff09\uff0c\u8fd9\u91cc\u63d0\u4f9b\u7b49\u4ef7\u5b9e\u73b0 */\n'
    '#ifndef kvmalloc\n'
    '#include <linux/mm.h>\n'
    '#include <linux/vmalloc.h>\n'
    'static inline void *kvmalloc(size_t size, gfp_t flags)\n'
    '{\n'
    '\tvoid *buf = kmalloc(size, flags);\n'
    '\tif (!buf)\n'
    '\t\tbuf = vmalloc(size);\n'
    '\treturn buf;\n'
    '}\n'
    'static inline void kvfree(const void *buf)\n'
    '{\n'
    '\tif (is_vmalloc_addr(buf))\n'
    '\t\tvfree(buf);\n'
    '\telse\n'
    '\t\tkfree(buf);\n'
    '}\n'
    '#endif\n'
)

anchor = '#include <linux/version.h>'
if anchor in s and 'static inline void *kvmalloc' not in s:
    s = s.replace(anchor, anchor + '\n' + SHIM, 1)
    f.write_text(s)
    print('shim moved after <linux/version.h>')
elif 'static inline void *kvmalloc' in s:
    print('shim already present after includes')
else:
    print('anchor not found!')

print('--- head 32 lines ---')
print('\n'.join(f.read_text().splitlines()[:32]))
