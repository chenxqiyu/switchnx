import pathlib
import re
import collections

KSU = pathlib.Path('/root/nxbuild/kernel-src/drivers/kernelsu')
INC = pathlib.Path('/root/nxbuild/kernel-src/include')

pat = re.compile(r'#\s*include\s*<linux/([A-Za-z0-9_./-]+\.h)>')
need = collections.Counter()
for f in KSU.rglob('*'):
    if f.suffix not in ('.c', '.h'):
        continue
    try:
        txt = f.read_text(errors='ignore')
    except OSError:
        continue
    for m in pat.finditer(txt):
        need[m.group(1)] += 1

missing = []
for h, cnt in sorted(need.items()):
    p = INC / 'linux' / h
    if not p.exists():
        missing.append((h, cnt))

print('KSU 引用的 linux/ 头文件总数: %d' % len(need))
print('在 4.9 树中缺失的: %d' % len(missing))
for h, cnt in missing:
    print('  %-34s 被引用 %d 次' % (h, cnt))
