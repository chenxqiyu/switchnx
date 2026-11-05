import tarfile, struct, pathlib, json, collections, sys

tgz = pathlib.Path(r'F:\core\switchkernel\modules.tgz')
CRC = {}
conflicts = collections.defaultdict(set)
n_ko = n_ok = 0
vermagics = collections.Counter()

SH = '<IIQQQQIIQQ'

def parse_ko(d):
    global n_ok
    if d[:4] != b'\x7fELF' or d[4] != 2:
        return None, None
    e_shoff = struct.unpack_from('<Q', d, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', d, 0x3a)[0]
    e_shnum = struct.unpack_from('<H', d, 0x3c)[0]
    e_shstrndx = struct.unpack_from('<H', d, 0x3e)[0]
    shs = []
    for i in range(e_shnum):
        v = struct.unpack_from(SH, d, e_shoff + i * e_shentsize)
        shs.append({'nameoff': v[0], 'off': v[4], 'size': v[5]})
    if e_shstrndx >= len(shs):
        return None, None
    base = shs[e_shstrndx]['off']
    def sname(n):
        try:
            return d[base + n:d.index(b'\0', base + n)].decode()
        except Exception:
            return ''
    ver = mi = None
    for s in shs:
        nm = sname(s['nameoff'])
        if nm == '__versions':
            ver = s
        elif nm == '.modinfo':
            mi = s
    vm = None
    if mi:
        for kv in d[mi['off']:mi['off'] + mi['size']].split(b'\0'):
            if kv.startswith(b'vermagic='):
                vm = kv[9:].decode('latin1', 'replace')
    items = []
    if ver and ver['size'] >= 64:
        for i in range(ver['size'] // 64):
            off = ver['off'] + i * 64
            crc = struct.unpack_from('<Q', d, off)[0] & 0xFFFFFFFF
            name = d[off + 8:off + 64].split(b'\0')[0].decode('latin1', 'replace')
            if name:
                items.append((name, crc))
        n_ok += 1
    return items, vm


with tarfile.open(tgz) as tf:
    for m in tf:
        if not m.name.endswith('.ko'):
            continue
        n_ko += 1
        items, vm = parse_ko(tf.extractfile(m).read())
        if vm:
            vermagics[vm] += 1
        if not items:
            continue
        for name, crc in items:
            if name in CRC and CRC[name] != crc:
                conflicts[name].add(CRC[name])
                conflicts[name].add(crc)
            CRC[name] = crc

print('模块总数: %d，成功解析 __versions: %d' % (n_ko, n_ok))
print('汇总符号数: %d' % len(CRC))
print('CRC 冲突符号: %d %s' % (len(conflicts), list(conflicts)[:5]))
print()
print('vermagic 分布:')
for v, c in vermagics.most_common(5):
    print('  %4dx %s' % (c, v))

pathlib.Path(r'F:\core\switchkernel\_factory_crc.json').write_text(json.dumps(CRC), encoding='utf-8')
print()
print('已保存 _factory_crc.json')
for k in ('module_layout', 'printk', 'kfree', 'memcpy', 'msleep', '__kmalloc'):
    print('  %-16s 0x%08x' % (k, CRC.get(k, 0)))
