import pathlib

p = pathlib.Path('/root/nxbuild/nvidia/drivers/video/tegra/host/Makefile')
s = p.read_text()

old = '\txxd -i $< >> $@\n'
new = '\txxd -i $< | tail -n +2 | head -n -2 >> $@\n'

if 'head -n -2' in s:
    print('already patched')
elif old in s:
    s = s.replace(old, new, 1)
    p.write_text(s)
    print('patched: strip xxd own declaration/len lines')
else:
    print('PATTERN NOT FOUND, lines containing xxd:')
    for i, l in enumerate(s.splitlines(), 1):
        if 'xxd' in l:
            print(i, repr(l))
