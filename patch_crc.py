#!/usr/bin/env python3
"""把 vmlinux 中 __kcrctab / __kcrctab_gpl 里的符号 CRC 改写成原厂值。

背景：本源码树用 gcc 6.4 + 当前 genksyms 算出的符号 CRC 与原厂内核系统性不一致
（例如 module_layout：我们 0xb1435381，原厂 0x71e39146），但 struct module 等
类型布局实测完全相同（sizeof = 832 一致），配置也几乎一致。CRC 只是类型签名哈希，
改写它不影响实际 ABI，却能让原厂 /vendor/lib/modules/*.ko 正常通过校验加载。

用法: python3 patch_crc.py <vmlinux> <factory_crc.json> [--dry-run]
"""
import sys
import json
import struct
import shutil
import pathlib

SH_FMT = '<IIQQQQIIQQ'


class Elf:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.data = bytearray(self.path.read_bytes())
        d = self.data
        assert d[:4] == b'\x7fELF' and d[4] == 2 and d[5] == 1, 'need ELF64 LE'
        self.e_shoff = struct.unpack_from('<Q', d, 0x28)[0]
        self.e_shentsize = struct.unpack_from('<H', d, 0x3a)[0]
        self.e_shnum = struct.unpack_from('<H', d, 0x3c)[0]
        self.e_shstrndx = struct.unpack_from('<H', d, 0x3e)[0]
        self.sections = []
        for i in range(self.e_shnum):
            v = struct.unpack_from(SH_FMT, d, self.e_shoff + i * self.e_shentsize)
            self.sections.append({
                'nameoff': v[0], 'type': v[1], 'flags': v[2],
                'addr': v[3], 'off': v[4], 'size': v[5],
            })
        base = self.sections[self.e_shstrndx]['off']
        for s in self.sections:
            n = s['nameoff']
            end = d.index(b'\0', base + n)
            s['name'] = bytes(d[base + n:end]).decode('latin1')
        # 程序头，建立 vaddr -> file offset 映射
        e_phoff = struct.unpack_from('<Q', d, 0x20)[0]
        e_phentsize = struct.unpack_from('<H', d, 0x36)[0]
        e_phnum = struct.unpack_from('<H', d, 0x38)[0]
        self.loads = []
        for i in range(e_phnum):
            o = e_phoff + i * e_phentsize
            p_type = struct.unpack_from('<I', d, o)[0]
            if p_type != 1:
                continue
            p_offset = struct.unpack_from('<Q', d, o + 8)[0]
            p_vaddr = struct.unpack_from('<Q', d, o + 16)[0]
            p_filesz = struct.unpack_from('<Q', d, o + 32)[0]
            self.loads.append((p_vaddr, p_vaddr + p_filesz, p_offset))

    def vaddr_to_off(self, addr):
        for lo, hi, off in self.loads:
            if lo <= addr < hi:
                return off + (addr - lo)
        return None

    def cstr(self, addr, limit=200):
        off = self.vaddr_to_off(addr)
        if off is None:
            return None
        return self.cstr_at_off(off, limit)

    def cstr_at_off(self, off, limit=200):
        if off is None or off < 0 or off >= len(self.data):
            return None
        try:
            end = self.data.index(b'\0', off, off + limit)
        except ValueError:
            return None
        s = bytes(self.data[off:end]).decode('latin1', 'replace')
        if not s or not all(32 <= ord(ch) < 127 for ch in s):
            return None
        return s

    def find(self, *names):
        for s in self.sections:
            if s['name'] in names:
                return s
        return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    vmlinux, crc_json = sys.argv[1], sys.argv[2]
    dry = '--dry-run' in sys.argv

    factory = json.loads(pathlib.Path(crc_json).read_text())
    e = Elf(vmlinux)

    pairs = [
        ('__ksymtab', '__kcrctab'),
        ('__ksymtab_gpl', '__kcrctab_gpl'),
        ('___ksymtab', '___kcrctab'),
        ('___ksymtab_gpl', '___kcrctab_gpl'),
    ]

    total = patched = same = missing = 0
    samples = []
    touched_ranges = []

    for kst_name, kcr_name in pairs:
        kst = e.find(kst_name)
        kcr = e.find(kcr_name)
        if not kst or not kcr:
            continue
        n_crc = kcr['size'] // 4
        # arm64 4.9 用 PREL32：struct kernel_symbol { int value_offset; int name_offset; } = 8 字节
        if kst['size'] // 8 == n_crc:
            ent, prel32 = 8, True
        elif kst['size'] // 16 == n_crc:
            ent, prel32 = 16, False
        else:
            print('[warn] 无法判定 %s 条目大小（size=%d, crc 条数=%d），跳过'
                  % (kst_name, kst['size'], n_crc))
            continue
        n = n_crc
        print('[info] %s: %d 条 x %d 字节 (%s), CRC 表 %s 文件偏移 0x%x'
              % (kst_name, n, ent, 'PREL32' if prel32 else 'ABS', kcr_name, kcr['off']))

        for i in range(n):
            s_off = kst['off'] + i * ent
            if prel32:
                voff, noff = struct.unpack_from('<ii', e.data, s_off)
                name = e.cstr_at_off(s_off + 4 + noff)
                if i < 3:
                    print('    [dbg] entry %d raw=%s voff=%d noff=%d nameoff=0x%x -> %r'
                          % (i, bytes(e.data[s_off:s_off + 8]).hex(), voff, noff,
                             s_off + 4 + noff, name))
            else:
                _value, name_ptr = struct.unpack_from('<QQ', e.data, s_off)
                name = e.cstr(name_ptr)
            if not name:
                continue
            total += 1
            want = factory.get(name)
            if want is None:
                missing += 1
                continue
            c_off = kcr['off'] + i * 4
            cur = struct.unpack_from('<I', e.data, c_off)[0]
            if cur == want:
                same += 1
                continue
            patched += 1
            if len(samples) < 12:
                samples.append((name, cur, want))
            struct.pack_into('<I', e.data, c_off, want)
            touched_ranges.append(c_off)

    print()
    print('共有导出符号 %d 个' % total)
    print('  CRC 已一致    : %d' % same)
    print('  需改写        : %d' % patched)
    print('  原厂表中没有  : %d （保持原值，模块用不到）' % missing)
    print()
    if samples:
        print('改写样例：')
        for name, cur, want in samples:
            print('  %-34s 0x%08x -> 0x%08x' % (name, cur, want))

    if dry:
        print('\n[dry-run] 未写回文件')
        return 0
    if patched == 0:
        print('\n无需修改')
        return 0

    bak = pathlib.Path(vmlinux + '.orig')
    if not bak.exists():
        shutil.copy2(vmlinux, bak)
        print('\n已备份: %s' % bak)
    pathlib.Path(vmlinux).write_bytes(bytes(e.data))
    print('已写回 %s（改写 %d 处）' % (vmlinux, patched))
    return 0


if __name__ == '__main__':
    sys.exit(main())
