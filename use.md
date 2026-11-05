# Nintendo Switch (icosa) 容器化内核 — 使用说明

> 最后更新：2026-11-05 12:40（已实测开机成功，容器能力验证通过）

## 一、这是什么

给 **Nintendo Switch（代号 icosa，Tegra X1 T210）** 编译的 LineageOS 17.1（Android 10）内核，
在原厂内核基础上打开了 **Docker / 容器化（Droidspace）所必需、但原厂关掉的内核能力**。

- 内核版本：`4.9.140-gac6058b04336-dirty`（与原厂逐字符一致）
- 源码基线：`makinbacon21/android_kernel_nvidia_kernel-4.9-nx` 的 **`lineage-17.1`** 分支
- commit：`ac6058b0433618d3760c623e13531bad67d4e397`（= 设备原厂内核源码）
- 编译器：**gcc 6.4**（必须，不能用 gcc 12/14，见附录）
- root 方案：沿用 Magisk，不含 KernelSU

### 新开的内核配置

| 类别 | 配置项 | 原厂状态 |
|---|---|---|
| 命名空间 | `NAMESPACES` `PID_NS` `NET_NS` `UTS_NS` `IPC_NS` `SYSVIPC` | 全部不存在 / `=n` |
| cgroup v1 | `CGROUPS` `MEMCG` `CGROUP_DEVICE/FREEZER/PIDS` `CPUSETS` `BLK_CGROUP` | 部分 |
| 网络 | `VETH` `BRIDGE` `BRIDGE_NETFILTER` `NF_NAT` `IP_NF_NAT` `IP_NF_TARGET_MASQUERADE` `XT_MATCH_CONNTRACK` 等 | 部分 |
| 存储 | `OVERLAY_FS` | `=n` |

**原厂内核 `CONFIG_NAMESPACES=n`，根本无法跑容器**，这是本次改动的核心目的。

### ⚠️ 最重要的一点：必须同时替换系统模块

打开命名空间会**真实改变内核结构体布局**（例如 4.9 的 `struct net` 在 `CONFIG_NET_NS=n` 时是空壳，
开启后变成完整定义 → `struct nsproxy` 变大 → `struct task_struct` 变大）。

后果：**所有带结构体参数的导出符号 ABI 全部变化**，原厂 313 个 `.ko` 一个都加载不了。

所以刷内核 **必须同时**把 `/vendor/lib/modules/*.ko` 换成同源编译的版本，
**只刷内核必然黑屏**。本目录已提供 `flat_modules.tgz`（309 个模块）。

---

## 二、文件清单

目录：`F:\core\switchkernel\`

| 文件 | 大小 | md5 | 用途 |
|---|---|---|---|
| `boot_icosa_docker.img` | 11.59 MB | `9be8083dfc7c6ed19cd0e24f612c37c4` | **内核**，dd 写入 LNX |
| `flat_modules.tgz` | 7.4 MB | `aca845518bff897ea46e41e4ffec32d5` | **配套模块**（309 个 .ko，解到 /vendor/lib/modules） |
| `cywifi.tgz` | 463 KB | — | **WiFi 驱动**（cypress backports 4 个 .ko，解到 cypress-fmac-upstream 目录） |
| `lnx_backup_20261105.img` | 32 MB | `c5e194aa3df4edda46b4fa7a34c6419c` | 原始 boot 备份（救砖） |
| `modules.tgz` | 7.8 MB | — | 原始 vendor 模块备份（含 313 个，用于还原） |
| `Image.gz` | 11.22 MB | `103c5b48c27aa5622466b5efbcf04552` | 纯内核镜像 |
| `use.md` | — | — | 本文件 |

分区：`LNX` → `/dev/block/mmcblk0p4`（32 MB，非 A/B）；`/vendor` → `/dev/block/mmcblk0p2`（0.9 GB）。

---

## 三、刷入（两部分，缺一不可）

> 前提：设备在 Android 或 TWRP，adb 可用。

### 3.1 刷内核（dd 直刷）

```bash
adb push boot_icosa_docker.img /sdcard/boot_v5.img
adb shell su -c "dd if=/sdcard/boot_v5.img of=/dev/block/by-name/LNX bs=4096; sync"
```

### 3.2 替换系统模块（关键，别漏）

**方式 A：TWRP 里操作（推荐，最稳）**

```bash
adb push flat_modules.tgz /sdcard/
adb shell "mount -o rw,remount /vendor"
adb shell "cd /vendor/lib/modules && tar xzf /sdcard/flat_modules.tgz"
adb shell "restorecon -R /vendor/lib/modules"   # 修 SELinux 上下文
adb shell "sync"
```

**方式 B：Android 已启动时（需 root / adb root）**

```bash
adb root
adb push flat_modules.tgz /sdcard/
adb shell "mount -o rw,remount /vendor"
adb shell "cd /vendor/lib/modules && tar xzf /sdcard/flat_modules.tgz && sync"
adb shell "restorecon -R /vendor/lib/modules"
```

### 3.3 重启

```bash
adb reboot
```

boot 分区只在开机时读一次，**必须重启才生效**。Switch 重启后可能需要手动在 Hekate 里选 Android。

---

## 四、验证

```bash
# 1. 内核版本（必须精确等于原厂串）
adb shell uname -r
# → 4.9.140-gac6058b04336-dirty

# 2. 模块是否真的加载（关键，>50 个说明正常）
adb shell lsmod | wc -l

# 3. 容器配置
adb shell "zcat /proc/config.gz | grep -E '^CONFIG_(NAMESPACES|NET_NS|PID_NS|VETH|OVERLAY_FS)='"

# 4. 命名空间实测（最关键）
adb shell "unshare --net --pid --fork true && echo CONTAINER_OK"
# → CONTAINER_OK
```

### 本次实测结果（2026-11-05 12:33）

```
uname -r                             4.9.140-gac6058b04336-dirty
sys.boot_completed                   1
init.svc.zygote                       running
init.svc.surfaceflinger               running
lsmod                                59 个模块
nvgpu                                已加载（被 87 处引用）
DisplayDeviceInfo                    内置屏幕 1280x720, state ON
unshare --net --pid --fork true      CONTAINER_OK
unshare --net --pid --uts --ipc      ALL_OK
前台 Activity                        com.google.android.tvlauncher
```

截图验证画面正常（本目录 `screen_now.png`）。

---

## 五、回滚

### 5.1 只回滚内核（vendor 模块已换，仍需回滚模块才能完全恢复）

```bash
adb shell su -c "dd if=/sdcard/lnx_backup_20261105.img of=/dev/block/by-name/LNX; sync"
```

### 5.2 完整回滚（内核 + 模块）

```bash
# 内核
adb shell "dd if=/sdcard/lnx_backup_20261105.img of=/dev/block/by-name/LNX bs=4096; sync"

# 模块（用原厂备份覆盖回去）
adb push modules.tgz /sdcard/
adb shell "mount -o rw,remount /vendor"
adb shell "cd /vendor/lib && tar xzf /sdcard/modules.tgz"
adb shell "restorecon -R /vendor/lib/modules; sync"

adb reboot
```

### 5.3 起不来（黑屏 / bootloop）

用 Hekate 进 TWRP，执行 5.2 的两条命令（TWRP 里不需要 `su -c`，直接执行）。
备份文件在设备 `/sdcard/` 和电脑 `F:\core\switchkernel\` 各一份，md5 一致。

---

## 六、已知问题

### 6.1 Magisk 未启动（当前状态）

- 现象：`/system/bin/su` 不存在，无 `magiskd` 进程；`/cache/magisk.log` 停留在 11:19（原厂内核那次）
- dmesg 证据：`SELinux: Context u:object_r:magisk_file:s0 is not valid (left unmapped)`
  → Magisk 的 sepolicy 补丁没生效
- **Magisk 数据完好**：`/data/adb/magisk/` 工具齐全，`/data/adb/modules/` 下
  `droidspaces`、`zygisk_lsposed`、`zygisk_il2cpp_mcp`、`ce-frida` 等模块目录完整
- 影响：`droidspaces` 等 Magisk 模块暂时不生效；但**内核层容器能力已可用**（unshare 验证通过）
- 处理建议：进 TWRP 用 Magisk 31.0 的 zip 重新 patch 当前 boot（会基于新内核重新生成 ramdisk），
  或系统内用 Magisk Manager「安装 → 直接安装（推荐）」

### 6.2 WiFi（已修复）

原厂 WiFi 驱动在 `/vendor/lib/modules/cypress-fmac-upstream/`（compat / cfg80211 / brcmutil / brcmfmac），
是 **Cypress backports v5.4.18** 编的，源码树里没有，无法直接重编 → 一开始 WiFi 完全不可用。

**修复方法**：用对应源码仓库同源重编这 4 个模块：

- 源码：`Modded-ArrowOS-For-Switch/android_kernel_nvidia_cypress-fmac-upstream` @ `lineage-17.1`
- 版本：cypress backports `v5.4.18-2020_0925`
- 编出来的 4 个 .ko 与原厂体积几乎一致（brcmfmac 504448 vs 507880）

**为什么内核树自带的 brcmfmac 不能用**：它只能走 escan，而 cypress 7.35 固件对 escan 请求返回
`BCME_BADARG (-4)`（`brcmf_run_escan: error (-4)`）；该版本还移除了 legacy `BRCMF_C_SCAN` 的结果
上报路径，无路可退。backports 驱动则与固件配套。

**刷入**：

```bash
adb push cywifi.tgz /sdcard/
adb shell "mount -o rw,remount /vendor"
adb shell "cd /vendor/lib/modules/cypress-fmac-upstream && tar xzf /sdcard/cywifi.tgz"
adb shell "cp -f /vendor/lib/modules/cypress-fmac-upstream/cfg80211.ko /vendor/lib/modules/"
adb shell "restorecon -R /vendor/lib/modules; sync"
adb reboot
```

**固件路径补充**（必要，只做一次）：内核树 backports 默认在 `brcm/` 子目录找固件，
需把 `/vendor/firmware/brcmfmac4356-pcie.*` 复制到 `/vendor/firmware/brcm/`：

```bash
adb shell "mkdir -p /vendor/firmware/brcm && cd /vendor/firmware && \
  cp brcmfmac4356-pcie.bin brcmfmac4356-pcie.clm_blob \
     'brcmfmac4356-pcie.nintendo,icosa.txt' brcm/ && \
  cp brcm/brcmfmac4356-pcie.nintendo,icosa.txt brcm/brcmfmac4356-pcie.txt"
```

**实测结果**：自动连上 5GHz AP，`RSSI -42`、`866Mbps`、`inet 192.168.1.124/24`、
`ping 223.5.5.5` 0% 丢包，dmesg 零 `escan` 错误。

### 6.3 cgroup 挂载方式

设备是 cgroup v1，子系统已分别挂在 `/dev/cpuctl`、`/dev/memcg`、`/dev/blkio`、`/dev/cpuset`，
`/sys/fs/cgroup` 为空。同一子系统 v1 只能挂一次，容器运行时要 **bind 挂载**已有挂载点，
不能重新 `mount cgroup`（必然 EBUSY）。

### 6.4 内核体积

`Image.gz` 11.22 MB（原厂 11.45 MB，反而更小），boot.img 11.59 MB，远小于 32 MB 分区。

---

## 七、附录：重新编译

### 7.1 环境（实测可用）

- 构建机：Debian 13（x86_64），4 核 / 19G
- 交叉编译器：**gcc 6.4**（Ubuntu bionic 的 `aarch64-linux-gnu-gcc-6`，6.4.0）
  - 安装：从清华源下 4 个包 `gcc-6-aarch64-linux-gnu`、`gcc-6-aarch64-linux-gnu-base`、
    `cpp-6-aarch64-linux-gnu`、`libgcc-6-dev-arm64-cross`（均 `6.4.0-17ubuntu1cross1`），
    再补 `libisl19_0.19-1_amd64.deb`，`dpkg -i --force-depends`
  - 软链到 `/root/nxbuild/tc/bin/aarch64-linux-gnu-*`（去掉 `-6` 后缀）并前置 PATH
- ⚠️ **gcc 12 / 14 编 4.9 内核不可用**：能编过但生成的机器码在 Tegra X1 上跑不起来
  （原厂就是 gcc 6.4，`linux_banner` 里能看到）
- 必须装：`bc flex bison libssl-dev libelf-dev libncurses-dev xxd lz4 ccache cpio`

### 7.2 目录结构（必须）

```
/root/nxbuild/
├── kernel-src/     # 主树：makinbacon21/...-4.9-nx @ lineage-17.1
├── nvidia/         # overlay 1（必需）
├── nvgpu/          # overlay 2（必需，缺了 GPU 驱动编不出来）
└── tc/bin/         # gcc-6 软链，PATH 前置
```

主树 `Makefile` 顶部：
```make
KERNEL_OVERLAYS += $(CURDIR)/../nvidia
KERNEL_OVERLAYS += $(CURDIR)/../nvgpu
KERNEL_OVERLAYS += $(CURDIR)/../nvgpu-next
KERNEL_OVERLAYS += $(CURDIR)/../nvidia-t23x
```

- `nvidia` overlay：`Modded-ArrowOS-For-Switch/android_kernel_nvidia_linux-4.9_icosa_kernel_nvidia` @ `lineage-17.1`
  （提供 `tegra_prod`、`arm-smmu-suspend`、`tegra_profiler`、eqos 等）
- `nvgpu` overlay：`LineageOS/android_kernel_nvidia_linux-4.9_kernel_nvgpu` @ `lineage-17.1`
  （提供 `drivers/gpu/nvgpu`，缺了会静默丢掉 14 个 GK20A 配置 → 黑屏）
- ⚠️ `nvgpu/drivers/gpu/Makefile` 里的 `obj-$(CONFIG_GK20A) += nvgpu/` **不会自动生效**
  （Makefile 不走 overlay 搜索），必须手工追加到 `kernel-src/drivers/gpu/Makefile`

### 7.3 版本串固定（必须）

`UTS_RELEASE` = `VERSION.PATCHLEVEL.SUBLEVEL` + `scripts/setlocalversion` 的输出，
`CONFIG_LOCALVERSION` **不参与**。`--depth 1` clone 无 tag 时只能给出 8 位 hash 且带 `+`，
会导致模块 vermagic 不匹配。

把 `scripts/setlocalversion` 换成：

```sh
#!/bin/sh
echo "-gac6058b04336-dirty"
```

### 7.4 编译命令

```bash
export PATH=/root/nxbuild/tc/bin:$PATH
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
cd /root/nxbuild/kernel-src

make tegra_android_defconfig
scripts/config --enable NAMESPACES --enable PID_NS --enable NET_NS \
  --enable UTS_NS --enable IPC_NS --enable SYSVIPC \
  --enable VETH --enable BRIDGE --enable OVERLAY_FS --enable MEMCG
make olddefconfig

# 内核
make -j$(nproc) Image.gz
# 模块（必须，否则黑屏）
make -j$(nproc) modules
```

gcc 6 不需要任何 `-Wno-error` 之类的放宽参数（那些是 gcc 12 才需要的）。

### 7.5 打包

```bash
# 内核 boot.img：用原厂 boot 备份 + 新 Image.gz 重打包（pack_boot.py）
python3 pack_boot.py

# 模块：扁平打包（所有 .ko 一层，方便直接解到 /vendor/lib/modules）
mkdir -p kolist && find kernel-src -name '*.ko' -exec cp {} kolist/ \;
tar czf flat_modules.tgz -C kolist .
```

> `pack_boot.py` 注意：原 LNX 备份是 32 MB 整分区，尾部 21.7 MB 全零填充，
> 必须 strip 再拼装，否则超过 32 MB 会写坏后续分区。

### 7.6 编译 WiFi 驱动（cypress backports）

```bash
cd /root/nxbuild
git clone --depth 1 -b lineage-17.1 \
  https://github.com/Modded-ArrowOS-For-Switch/android_kernel_nvidia_cypress-fmac-upstream.git cypress
cd cypress/backports-wireless
chmod -R +x scripts kconf
export PATH=/root/nxbuild/tc/bin:$PATH

# 注意必须显式传 HOSTCC，否则 backports 的 Makefile 会把 -Wall 当命令执行
make HOSTCC=gcc HOSTCXX=g++ HOSTLD=ld ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     KLIB=/root/nxbuild/kernel-src KLIB_BUILD=/root/nxbuild/kernel-src defconfig-brcmfmac

make -j4 HOSTCC=gcc HOSTCXX=g++ HOSTLD=ld ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     KLIB=/root/nxbuild/kernel-src KLIB_BUILD=/root/nxbuild/kernel-src modules
```

产物 4 个（路径相对 `backports-wireless/`）：

```
compat/compat.ko
net/wireless/cfg80211.ko
drivers/net/wireless/broadcom/brcm80211/brcmutil/brcmutil.ko
drivers/net/wireless/broadcom/brcm80211/brcmfmac/brcmfmac.ko
```

全部 `strip --strip-unneeded` 后打进一个 tar，扁平结构。

> 注意：`KLIB` 指向已编译好的内核树即可（需要其中已有 `Module.symvers` 和 `include/generated`）。

### 7.7 踩过的坑（按重要性排序）

1. **只刷内核不换模块 = 黑屏**（ABI 冲突，本项目最大坑，见第一节）
2. **必须用 gcc 6.4**，gcc 12/14 编出来能过但跑不起来
3. **必须补 `nvgpu` overlay**，否则 GPU 驱动缺失（14 个 GK20A 配置被静默丢弃）
4. **版本串必须精确等于 `4.9.140-gac6058b04336-dirty`**，否则 vermagic 不匹配
5. **`CONFIG_MODVERSIONS` 不能关**，它是 vermagic 字符串的一部分
6. 主树缺 `include/linux/tegra_prod.h` 等 → 靠 overlay 补齐，不要手工改 Kconfig
7. `nvidia/drivers/video/tegra/host/Makefile` 的 `xxd -i` 规则要改成
   `xxd -i $< | tail -n +2 | head -n -2`（新版 xxd 会重复输出变量定义）
8. 编译中断会留下 0 字节 `built-in.o`，链接报 `undefined symbol 'jiffies_64'`：
   `find . -name '*.o' -size 0 -delete`
9. `__ksymtab` 在 vmlinux/Image 里全 0 是**正常的**（arm64 PIE，启动时自举重定位填充），不要误判
10. 上传到设备/编译机的 `.sh` 必须是 LF 行尾，否则 bash 报 `$'\r'`
