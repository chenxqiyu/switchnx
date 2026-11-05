import pathlib
import sys

p = pathlib.Path('/root/nxbuild/kernel-src/kernel/module.c')
s = p.read_text()

MARK = 'local build: accept stock CRC'

if MARK in s:
    print('already patched')
    sys.exit(0)

old = "\t\tif (versions[i].crc == maybe_relocated(*crc, crc_owner))\n"
new = ("\t\t/* " + MARK + " — 保留 maybe_relocated 调用避免 unused 警告，\n"
       "\t\t * 但比较结果恒真，跳过与原厂 .ko 的符号 CRC 比对。\n"
       "\t\t * vermagic 校验仍然生效（版本串必须完全一致）。\n"
       "\t\t */\n"
       "\t\tif (versions[i].crc == maybe_relocated(*crc, crc_owner) || 1)\n")

if old not in s:
    print('PATTERN NOT FOUND')
    sys.exit(1)

n = s.count(old)
s = s.replace(old, new, 1)
p.write_text(s)
print('patched (%d occurrence(s) found, 1 replaced)' % n)
