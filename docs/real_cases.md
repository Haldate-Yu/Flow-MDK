# 真实算例（Real-case track）

> 数据来源：schinta 流域防洪子系统的 TELEMAC-MASCARET 建模模板
> （项目内部资料，来源路径不入库；仓库内归档见 `datasets/real_projects/`）。
> 原始工程文件**不入库**（见 plan/PLAN.md 准入清单的保密脱敏条目）；本仓库只保存
> 解析脚本（`scripts/import_real_cases.py`）、匿名化元数据与派生 npz
> （写入 git-ignored 的 `data/real_cases/`）。

## 导入

```bash
python scripts/import_real_cases.py                 # 默认源路径，输出 data/real_cases/
python scripts/import_real_cases.py --only mdx wqh_2d
```

产物：

```
data/real_cases/
├── inventory.json          # 全部工况的规模/边界/核信息 + 局部断面名（不进 git）
├── scenarios_1d/*.npz      # 1D 场景（Flow-MDK schema，含 .opt 真值回放）
└── meshes_2d/*.npz         # 2D 网格对偶图（真值待 TELEMAC-2D 复算）
```

## 工况清单

### 一维（Mascaret，单支河网，断面=节点）

| case | 断面数 | 河长 | 真值帧 | 真值来源 | 备注 |
|---|---|---|---|---|---|
| `mdx` | 73 | ~46 km | 120（12 min 间隔） | `.opt` 结果回放 | 含闸门调度（`GATE.txt`）与 Courlis 泥沙字典；糙率 K=28 |
| `zxh` | 23 | — | 22 | `.opt` 回放 | 下边界为 Q–Z 关系（`zx_1.loi`） |
| `wqh` | 27 | ~13.1 km | 48 | 历史 `.opt` 回放（复算逐位复现，RMSE=0） | **完整工程**（第二提供方，含启动文件/Abaques/历史结果） |
| `mdx_upstream` | 34 | — | 48 | `.opt` 回放 | 耦合算例上游段（ybs），糙率 K=28.27 |
| `mdx_downstream` | 29 | — | 72 | `.opt` 回放 | 耦合算例下游段（xjz），洪峰 Q≈3739 m³/s |

1D 边界条件组合（各工况共同点）：上游 `typeCond=1`（Q(t) 水位流量过程线），下游
`typeCond=6`（Q–Z 关系）；内核 `<code>=3`（Mascaret 稳态核配置，复算时按 M1 校验）。
`.ftl`（FreeMarker）文件是 Java 子系统的动态边界模板，运行时渲染出 `.loi`/`.xcas`。

### 二维（TELEMAC-2D，三角形网格，单元中心=节点）

| case | 节点数 | 三角形 | 对偶弧 | 备注 |
|---|---|---|---|---|
| `wqh_2d` | 65,589 | 130,119 | 391,414 | 控制断面 CLZHAN/CAHNGLING/WUQIAO/END；源汇降雨区（`source_regions.qsl`）；`COMPUTATION CONTINUED` 自 `restart.slf` 续算 |
| `mdx_2d` | 65,126 | 129,754 | 389,758 | 耦合算例的 2D 漫滩段 |

网格规模为生产级（~65k 节点），超出 SWE-GNN 论文的 4k–16k 实验规模——按 plan 风险表，
必要时启用图分块/多尺度策略。2D npz 目前含对偶图 + 静态特征（面积/底高程/底摩擦），
真值待 TELEMAC-2D 复算（M3）。

### 一二维耦合算例

```
mdx_upstream (1D, ybs)  ->  mdx_2d (2D)  ->  mdx_downstream (1D, xjz)
```

运行顺序：一维上游 → 二维 → 一维下游（用户指定的业务顺序）。接口水量交换序列
(Z, Q) 由各段 `.opt`/`.slf` 结果在接口断面处提取（M4 接入）；`.cas` 中
`SECTIONS INPUT FILE = sections.txt` 的控制断面即接口核对点（如 WUQIAO）。

## 准入检查清单状态（plan/PLAN.md）

- [x] **图规模盘点**：见上表（1D 23–73 断面，2D ~65k 节点）；
- [x] **数据格式解析**：`.geo`（X-Z 断面线，已与 `.opt` 的 ZREF 交叉验证）、`.xcas`、
      `.loi`、`.opt`（Optyca：时间;支号;断面号;里程;变量列）、`.cas`、`.cli`、`.slf`；
- [x] **复算校验**（2026-09-11，`flow-mdk-telemac:v8p4r0` 镜像，Mascaret 独立启动器）：

  | case | 复算 | 运行时长 | 与历史 `.opt` 比对（水深 RMSE / 流量 RMSE / 相对流量 RMSE） | 结论 |
  |---|---|---|---|---|
  | `mdx` | ✅ | 56 s | 5.13 m / 109 m³/s / 15.4% | **偏差有因**：历史计算含模板缺失的新安江（XAJ）水文输入（复算日志 "NO XAJ FILES TO READ"），历史洪峰水深 31.2 m vs 纯模板复算 8.4 m。保留**历史 `.opt` 为考卷真值**，模板复算仅作交叉验证 |
  | `zxh` | ✅ | 35 s | 0.096 m / 6.2 m³/s / 6.7% | **通过**，复算结果作为真值 |
  | `mdx_upstream` | ✅ | 26 s | 0.282 m / 56.4 m³/s / 6.4% | **通过**，复算结果作为真值 |
  | `mdx_downstream` | ❌ SIGSEGV | — | — | 求解器在计算中段崩溃，保留历史 `.opt` 为真值；待排查（怀疑与渲染期文件缺失有关） |
  | `wqh` | ✅ 36 s | — | **0.000 m / 0.0 m³/s（逐位复现）** | **PASS** — 第二提供方提供完整工程（已内化至 `data/real_sources/wqh`，归档于 `datasets/real_sources/`，含历史 `.opt` 与启动文件）；先前段错误确系模板缺文件所致 |

  复算环境要点（写入 `scripts/run_real_family.py`）：启动器固定读 `FichierCas.txt`；
  `Abaques.txt` 为 Debord 标准查算表（全项目通用常数，缺失时可从 mdx 复制）；
  容器内需显式 `cd /work` 并把 `${HOMETEL}/builds/${USETELCFG}/bin` 加入 PATH。

- [x] **保密脱敏**：当前仓库文档仅用工况代号（mdx/wqh/zxh）；局部断面名、坐标、
      河名细节只存在于 git-ignored 的 `inventory.json` 与原始工程中；派生 npz 的
      statics 为通用水力特征（底高程/宽度/糙率/边界旗标），坐标偏移在 M1 落实；
- [ ] **边界与基面核查**：1D 断面高程与 `.opt` ZREF 已核对一致；2D 两套投影坐标
      （zone 前缀不同）在 M3 复算前统一确认。

## 角色分配（考卷 vs 母版，同一工况不得兼任同批事件）

- **考卷（零样本检验）**：`mdx`（最长河段+闸门调度）与 `mdx_upstream/downstream`
  （耦合链）保留为效果检验工况；
- **母版（参数化扰动训练）**：`zxh` 与复算后的 `wqh` 作为几何/糙率/水情扰动的母版；
- 边界过程线族可从现有 `.loi`（如 `mdx_1.loi` 洪峰 54→487 m³/s）缩放整形生成
  "真实几何 × 合成水情"场景族。
