import pathlib

shim = (
    "/* \u517c\u5bb9\u57ab\u7247\uff1acompiler_types.h \u662f Linux 5.1 \u4ece compiler.h \u62c6\u5206\u51fa\u6765\u7684\uff0c\n"
    " * 4.9 \u6ca1\u6709\u8fd9\u4e2a\u5934\u6587\u4ef6\u3002KernelSU-Next \u76f4\u63a5 include \u4e86\u5b83\uff0c\u8fd9\u91cc\u8f6c\u53d1\u5230 compiler.h\u3002\n"
    " */\n"
    "#ifndef _LINUX_COMPILER_TYPES_H\n"
    "#define _LINUX_COMPILER_TYPES_H\n"
    "#include <linux/compiler.h>\n"
    "#endif\n"
)

p = pathlib.Path('/root/nxbuild/kernel-src/include/linux/compiler_types.h')
if not p.exists():
    p.write_text(shim)
    print('created', p)
else:
    print('already exists')

src = pathlib.Path('/root/nxbuild/kernel-src/drivers/kernelsu/feature/sulog.c')
print('--- sulog.c head ---')
print('\n'.join(src.read_text().splitlines()[:12]))
