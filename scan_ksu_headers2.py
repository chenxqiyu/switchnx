import pathlib
import re
import collections

SRC = pathlib.Path('/root/nxbuild/kernel-src')
KSU = SRC / 'drivers/kernelsu'

roots = [SRC / 'include' / 'linux', SRC / 'include' / 'uapi' / 'linux',
         SRC / 'arch' / 'arm64' / 'include' / 'linux']

def exists(rel):
    for r in roots:
        if (r / rel).exists():
            return True
    return False

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

missing = [(h, c) for h, c in sorted(need.items()) if not exists(h)]

print('KSU 引用 linux/ 头: %d 种' % len(need))
print('真正缺失: %d 种' % len(missing))
for h, c in missing:
    # 找出是哪个文件引用的
    users = []
    for f in KSU.rglob('*'):
        if f.suffix in ('.c', '.h'):
            try:
                if '<linux/%s>' % h in f.read_text(errors='ignore'):
                    users.append(str(f.relative_to(KSU)))
            except OSError:
                pass
    print('  %-28s x%-2d  %s' % (h, c, ', '.join(users[:3])))
