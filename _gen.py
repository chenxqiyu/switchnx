#!/usr/bin/env python
"""从 nx_magisk.yaml 生成本地可执行的分段构建脚本（LF 行尾）。"""
import pathlib

WF = pathlib.Path(r'F:\core\switchkernel\.github\workflows\nx_magisk.yaml')
OUT = pathlib.Path(r'F:\core\switchkernel')

src = WF.read_text(encoding='utf-8')
L = src.splitlines()

steps, cur = [], None
for i, l in enumerate(L):
    if l.startswith('    - name:'):
        if cur:
            steps.append(cur)
        cur = {'name': l.split(':', 1)[1].strip(), 'start': i, 'end': len(L)}
    elif cur is not None:
        cur['end'] = i
if cur:
    steps.append(cur)

WANT = {
    'Fix Missing Kconfig Dependencies': 's1_fix.sh',
    'Configure Kernel for Droidspace & Docker': 's2_config.sh',
    'Compile Custom Kernel': 's3_compile.sh',
    'Prepare AnyKernel3 Environment': 's4_ak3.sh',
    'Pack AnyKernel3 ZIP': 's5_pack.sh',
}

blocks = {}
for s in steps:
    if s['name'] not in WANT:
        continue
    seg = L[s['start']:s['end']]
    ri = next(i for i, x in enumerate(seg) if x.strip() == 'run: |')
    body = [x[8:] if x.startswith('        ') else x for x in seg[ri + 1:]]
    blocks[s['name']] = "\n".join(body).rstrip()

GUARD = (
    'cd /root/nxbuild/kernel-src || exit 1\n'
    'test -f Kconfig && test -d arch/arm64 || { echo "ERROR: not kernel tree root"; exit 1; }\n'
    'echo "[cwd] $(pwd)"'
)

SAFETY = (
    "if len(fixed) > 50:\n"
    "    print('ERROR: %d broken source lines - cwd likely wrong, aborting' % len(fixed))\n"
    "    raise SystemExit(1)\n"
    "print('disabled %d broken source line(s)' % len(fixed))"
)

HEAD = """#!/bin/bash
set -o pipefail
export http_proxy=http://192.168.1.244:10809
export https_proxy=http://192.168.1.244:10809
export PATH=/root/nxbuild/tc/bin:$PATH
echo '========== {name} =========='
"""

for name, fn in WANT.items():
    body = blocks[name]
    if 'cd kernel-src' in body:
        body = body.replace('cd kernel-src', GUARD, 1)
    else:
        body = 'cd /root/nxbuild || exit 1\n' + body

    body = body.replace(
        "print('disabled %d broken source line(s)' % len(fixed))", SAFETY)
    body = body.replace(
        'make -j$(nproc) Image.gz',
        'make -j$(nproc) Image.gz 2>&1 | tee /tmp/build.log')

    text = HEAD.format(name=name) + body + "\n"
    (OUT / fn).write_bytes(text.encode('utf-8'))
    print("generated %-14s %4d lines" % (fn, text.count("\n")))
