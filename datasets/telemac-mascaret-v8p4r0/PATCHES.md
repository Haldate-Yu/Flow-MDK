# Mascaret 内核补丁记录（v8p4r0 → Flow-MDK 补丁版）

本目录的构建上下文（`telemac-mascaret/`）相对原始 v8p4r0 带有一组本地修复。
原始文件备份与补丁 diff 见 `backups/<日期>/`；补丁版镜像 tag：
`flow-mdk-telemac:v8p4r0p1`（原镜像 `flow-mdk-telemac:v8p4r0` 保留可回档）。

## 2026-09-12 · XAJ 侧向入流未定义行为 + 上游 Q 边界垃圾初始水深

**文件**：`telemac-mascaret/sources/mascaret/Mascaret/mascaret.f90`
**备份**：`backups/2026-09-12/mascaret.f90.orig`
**补丁**：`backups/2026-09-12/flowmdk_kernel_patch_2026-09-12.patch`

### 背景

Part A v2 批量真值生成中 ~1/3 场景随机 SIGSEGV（rc=139），与初始水面线、时间步、
床面形态、稳定化开关均无关（换任何组合都有一批固定失败）；真实母版家族当年的
22 例 zxh 段错误同属此类。用 `-g -O0 -fbacktrace -fcheck=all` 重编内核后拿到
符号化崩溃点 `mascaret.f90:1021`（XAJ 侧向入流插值，"MODIFIED BY MAURICE" 本地
功能块）。

### 根因（两处，均已在补丁中修复）

1. **XAJ 读取的未定义行为（主因）**：`READ_Q_XAJ`/`READ_X_XAJ` 无条件从工作目录
   打开 `Q_XAJ.txt`/`X_XAJ.txt`；文件不存在时 `allocate` 了空表但 **intent(out) 的
   `nlines`/`num_columns` 从未赋值**。主循环随后以垃圾索引读取 `X_XAJ(ICOLO)`、
   `X_XAJ(NCOLO)`、`Q_XAJ(ILINE,NCOLO+1)`——越界读随机堆内存，命中未映射页即
   SIGSEGV，否则结果带数值污染。这解释了失败的场景集随堆布局随机、且部分"通过"
   场景真值带微小系统偏差（全量重跑前后对比：81/89 个场景真值有 ≤0.16 m 级别的
   变化，重跑后为无污染真值）。
   **修复**：缺失分支定死空状态（`nlines=0`、`num_columns=1`、`X_XAJ(1)=1e20`
   哨兵），并给 `nlines` 补了空文件边界的初始化；此时调用方循环全部空转，
   `QIN` 保持原值（等效无侧向入流，与无 XAJ 数据的物理语义一致）。
2. **上游 Q 强加边界的垃圾 `YFIX`（次因，防御性修复）**：`PTZ(1)` 对流量律不携带
   水位（=0），`YFIX = 0 - 床面 = -床面高程`。上游断面逼近临界流
   （0.99 < FROD < FROLIM）时连续性分支执行 `CSUR(IS, YFIX)`、Riemann 分支
   （LIMITE）同样消费它——负水深进几何表查询属未定义访问（源码中原有的干净报错
   分支在此版本中被注释）。**修复**：上游流量边界时将 `YFIX` 回退为当前节点实际
   水深（急流入流时唯一物理一致的状态），亚临界运行时该值从不被消费，行为不变。

### 验证

- 回归：已通过场景用补丁内核重跑，`.opt` **逐位一致**（A1_002/A1_004 抽查）。
- 修复效果：Part A v2 全量重跑 89/130 → **126/130 通过**，且全部走上 SARAP 稳态
  初始化（不再需要回填 fallback）。
- 剩余 4 例（A1_017/A1_067/A2_006/A2_008）为另一类独立缺陷：`s1geo` 几何表负索引
  （`Index '-4' below lower bound of 1`，干涸极限工况），以干净运行时错误终止，
  待单独排查。

### 复现/回档

```bash
# 用补丁源码重建镜像（约 20–40 min）
docker build -t flow-mdk-telemac:v8p4r0p1 datasets/telemac-mascaret-v8p4r0/
# 或不重建镜像，注入补丁二进制（宿主机编译见下）
FLOW_MDK_MASCARET_BIN=/path/to/mascaret_patched.exe python scripts/run_partA_mascaret.py ...
# 回档：git/备份恢复 mascaret.f90 后重新 docker build 即回到 v8p4r0 行为
```

宿主机快速重编（不等整镜像）：在容器内对 `sources/mascaret` 执行
`make mascaret.exe DBG="-g -O0 -fbacktrace -fcheck=all"`（注意：v8p4 的
`sources/mascaret/Makefile` 链接清单落后于源码，缺 `m_profil_evolution.o` 等，
`make` 完成后需手动 `gfortran ... -o mascaret.exe $(find . -name "*.o")` 补链接）。
