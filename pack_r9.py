import struct, hashlib, pathlib
BASE = pathlib.Path(r'F:\core\switchkernel')
SRC = BASE / 'lnx_backup_20261105.img'
NEW_K = BASE / 'Image_userns.gz'
OUT = BASE / 'boot_icosa_ksu_r9_userns.img'
FULL = 33554432

d = SRC.read_bytes()
assert d[:8] == b'ANDROID!'
k_size, k_addr, r_size, r_addr, s_size, s_addr, t_addr, page, hdr_ver, os_ver = struct.unpack_from('<10I', d, 8)
align = lambda n, a: (n + a - 1) // a * a

k_off = page
r_off = k_off + align(k_size, page)
s_off = r_off + align(r_size, page)
tail_off = s_off + align(s_size, page)
ramdisk = d[r_off:r_off + r_size]
second = d[s_off:s_off + s_size]
tail = d[tail_off:].rstrip(b'\0') if tail_off < len(d) else b''

nk = NEW_K.read_bytes()
hdr = bytearray(d[:page])
struct.pack_into('<I', hdr, 8, len(nk))
struct.pack_into('<8I', hdr, 8 + 40 + 16 + 512, 0, 0, 0, 0, 0, 0, 0, 0)

out = bytearray()
out += hdr
out += nk + b'\0' * (align(len(nk), page) - len(nk))
out += ramdisk + b'\0' * (align(len(ramdisk), page) - len(ramdisk))
if second:
    out += second + b'\0' * (align(len(second), page) - len(second))
out += tail
if len(out) < FULL:
    out += b'\0' * (FULL - len(out))
out = out[:FULL]
OUT.write_bytes(out)

v = OUT.read_bytes()
f2 = struct.unpack_from('<10I', v, 8)
k2, r2, p2 = f2[0], f2[2], f2[7]
v_ram = v[p2 + align(k2, p2): p2 + align(k2, p2) + r2]
print('page=%d hdr_ver=%d' % (p2, f2[8]))
print('kernel  new=%s (%d bytes)' % (k2 == len(nk), k2))
print('ramdisk preserved=%s md5=%s' % (hashlib.md5(v_ram).hexdigest() == hashlib.md5(ramdisk).hexdigest(), hashlib.md5(v_ram).hexdigest()))
print('size=%d (%.2f MB)' % (len(v), len(v)/1048576))
print('md5=%s' % hashlib.md5(v).hexdigest())
