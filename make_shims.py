import pathlib

INC = pathlib.Path('/root/nxbuild/kernel-src/include/linux')

simple = {
    'pgtable.h': ('<asm/pgtable.h>', 'asm/pgtable.h'),
    'minmax.h': ('<linux/kernel.h>', 'kernel.h'),
    'hex.h': ('<linux/kernel.h>', 'kernel.h'),
    'kstrtox.h': ('<linux/kernel.h>', 'kernel.h'),
    'unaligned.h': ('<asm/unaligned.h>', 'asm/unaligned.h'),
    'sched/signal.h': ('<linux/sched.h>', 'sched.h'),
    'sched/task.h': ('<linux/sched.h>', 'sched.h'),
    'sched/task_stack.h': ('<linux/sched.h>', 'sched.h'),
    'sched/mm.h': ('<linux/sched.h>', 'sched.h'),
    'sched/user.h': ('<linux/sched.h>', 'sched.h'),
}

created = []
for name, (target, real) in simple.items():
    p = INC / name
    if p.exists():
        continue
    p.parent.mkdir(parents=True, exist_ok=True)
    guard = '_LINUX_SHIM_' + name.replace('/', '_').replace('.', '_').upper()
    p.write_text(
        '/* \u517c\u5bb9\u57ab\u7247\uff1a%s \u5728 4.9 \u4e2d\u4e0d\u5b58\u5728\uff0c\u8f6c\u53d1\u5230 %s */\n'
        '#ifndef %s\n#define %s\n#include %s\n#endif\n' % (name, real, guard, guard, target)
    )
    created.append(name)

# overflow.h 需要真实实现（KSU 用到 check_*_overflow / size_* / struct_size）
p = INC / 'overflow.h'
if not p.exists():
    p.write_text(r'''/* 兼容垫片：4.9 分支没有 overflow.h，用编译器内建函数提供同等 API */
#ifndef _LINUX_OVERFLOW_SHIM_H
#define _LINUX_OVERFLOW_SHIM_H

#include <linux/types.h>
#include <linux/compiler.h>

#define check_add_overflow(a, b, d) ({		\
	typeof(a) __a = (a);			\
	typeof(b) __b = (b);			\
	typeof(d) __d = (d);			\
	(void) (&__a == &__b);			\
	__builtin_add_overflow(__a, __b, __d);	\
})

#define check_sub_overflow(a, b, d) ({		\
	typeof(a) __a = (a);			\
	typeof(b) __b = (b);			\
	typeof(d) __d = (d);			\
	(void) (&__a == &__b);			\
	__builtin_sub_overflow(__a, __b, __d);	\
})

#define check_mul_overflow(a, b, d) ({		\
	typeof(a) __a = (a);			\
	typeof(b) __b = (b);			\
	typeof(d) __d = (d);			\
	(void) (&__a == &__b);			\
	__builtin_mul_overflow(__a, __b, __d);	\
})

#define size_mul(a, b) ({			\
	size_t __r;				\
	if (__builtin_mul_overflow((size_t)(a), (size_t)(b), &__r))	\
		__r = (size_t)-1;		\
	__r;					\
})

#define size_add(a, b) ({			\
	size_t __r;				\
	if (__builtin_add_overflow((size_t)(a), (size_t)(b), &__r))	\
		__r = (size_t)-1;		\
	__r;					\
})

#define size_sub(a, b) ({			\
	size_t __r;				\
	if (__builtin_sub_overflow((size_t)(a), (size_t)(b), &__r))	\
		__r = (size_t)-1;		\
	__r;					\
})

#define array_size(a, b)	size_mul(a, b)
#define array3_size(a, b, c)	size_mul(size_mul(a, b), c)

#define struct_size(p, member, n)					\
	size_add(sizeof(*(p)), size_mul(sizeof((p)->member[0]), n))

#define flex_array_size(p, member, n)					\
	__ab_c_size(n, sizeof((p)->member[0]),			\
		    offsetof(typeof(*(p)), member))

#endif /* _LINUX_OVERFLOW_SHIM_H */
''')
    created.append('overflow.h')

print('created %d shims:' % len(created))
for c_ in created:
    print('  include/linux/' + c_)
