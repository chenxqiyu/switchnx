#!/usr/bin/env python
"""用设备原 boot 的 ramdisk + 新编译的 Image.gz，重打包成可 dd 直刷的 boot.img"""
import struct
import hashlib
import pathlib

BASE = pathlib.Path(r'F:\core\switchkernel')
SRC = BASE / 'lnx_backup_20261105.img'
NEW_K = BASE / 'Image.gz'
OUT = BASE / 'boot_icosa_docker.img'

d = SRC.read_bytes()
assert d[:8] == b'ANDROID!', 'not android boot image'

f = struct.unpack_from('<10I', d, 8)
(k_size, k_addr, r_size, r_addr, s_size, s_addr,
 t_addr, page, hdr_ver, os_ver) = f

print('原镜像: page=%d hdr_ver=%d kernel=%d ramdisk=%d second=%d' %
      (page, hdr_ver, k_size, r_size, s_size))


def align(n, a):
    return (n + a - 1) // a * a


k_off = page
r_off = k_off + align(k_size, page)
s_off = r_off + align(r_size, page)
tail_off = s_off + align(s_size, page)

ramdisk = d[r_off:r_off + r_size]
second = d[s_off:s_off + s_size]
# 原分区结尾是 32MB 整分区大小，尾部全是零填充，不能带进新镜像
tail_raw = d[tail_off:] if tail_off < len(d) else b''
tail = tail_raw.rstrip(b'\0')
print('尾部实际数据: %d 字节（原始 %d 字节，其余为零填充）' % (len(tail), len(tail_raw)))
print('ramdisk md5: %s (%d 字节)' % (hashlib.md5(ramdisk).hexdigest(), len(ramdisk)))

nk = NEW_K.read_bytes()
print('新 kernel: %d 字节 (原 %d)' % (len(nk), k_size))

hdr = bytearray(d[:1632])
struct.pack_into('<I', hdr, 8, len(nk))
struct.pack_into('<8I', hdr, 8 + 40 + 16 + 512, 0, 0, 0, 0, 0, 0, 0, 0)

out = bytearray()
out += hdr + b'\0' * (page - len(hdr))
out += nk + b'\0' * (align(len(nk), page) - len(nk))
out += ramdisk + b'\0' * (align(len(ramdisk), page) - len(ramdisk))
if second:
    out += second + b'\0' * (align(len(second), page) - len(second))
out += tail

OUT.write_bytes(out)
print('\n输出: %s  %.2f MB (%d 字节)' % (OUT.name, len(out) / 1048576, len(out)))

# 回读校验
v = OUT.read_bytes()
assert v[:8] == b'ANDROID!'
f2 = struct.unpack_from('<10I', v, 8)
k2, _, r2, _, s2, _, _, p2, hv2, _ = f2
v_r_off = p2 + align(k2, p2)
v_ram = v[v_r_off:v_r_off + r2]
print('校验: magic=OK page=%d hdr_ver=%d kernel_size=%d ramdisk_size=%d' % (p2, hv2, k2, r2))
print('ramdisk 是否原样保留:', 'YES' if hashlib.md5(v_ram).hexdigest() == hashlib.md5(ramdisk).hexdigest() else 'NO')
print('kernel 是否为新的:', 'YES' if k2 == len(nk) else 'NO')
print('boot.img md5:', hashlib.md5(v).hexdigest())
