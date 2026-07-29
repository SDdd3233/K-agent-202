---
name: lsdyna-kfile
description: 依据自然语言需求编写完整的 LS-DYNA k 文件（关键字输入卡组），并用本机求解器自动验证到可正常计算。覆盖碰撞、跌落、侵彻、成形、ALE、SPH 等显式动力学工况。当用户要求编写/修改/调试/检查 LS-DYNA 模型、k 文件、dyn/key 输入卡组，提到跌落仿真、碰撞仿真、侵彻计算等需求，或只有一个模糊的仿真想法需要梳理成完整方案时使用。
---

# LS-DYNA K 文件编写与自动验证

你的交付承诺：**一份通过本机求解器实际计算验证的完整 k 文件 + 一份验证报告**。
"写完就交"是不允许的——没跑通求解器、没过质检门槛的 deck 不是交付物。

以下把本文件所在目录称为 `SKILL_DIR`。所有脚本在 `SKILL_DIR/scripts/`，
知识库在 `SKILL_DIR/knowledge/`，经过验证的工况模板在 `SKILL_DIR/templates/`。

## 0. 环境自检（每个新会话第一次使用时做）

```bash
python "SKILL_DIR/scripts/kagent_config.py"    # 检查 4 个求解器 + mpiexec 路径
```

- 默认求解器：`C:\Program Files\ANSYS Inc\v242\ansys\bin\winx64`（LS-DYNA **R14.1.1**）。
  其他机器用环境变量 `LSDYNA_BIN`/`LSDYNA_MPIEXEC` 或 `~/.lsdyna-kagent.json` 覆盖。
- **版本红线：不使用比 R14 新的关键字或字段。** 手册是 R16 版，看到 "R15 及以上" 字样的功能一律回避。
- 手册 PDF 不在时先跑 `python "SKILL_DIR/scripts/fetch_manuals.py"`。
- 若任务需要文献参数检索，先检查 bundled academic MCP：
  `python "SKILL_DIR/vendor/nature-academic-search/scripts/preflight.py"`。
  `PUBMED_EMAIL` 可由环境变量提供；不得把邮箱、API key 或 Elsevier 配置写入 skill 包。

## 1. 需求头脑风暴与收敛 → 《仿真任务书》

用户的输入往往只是一个想法（"我想看看这个件摔了会不会坏"）。本阶段通过**迭代提问**
把它收敛成一份《仿真任务书》（spec.md）——后续建模、验证、交付的唯一契约。
完整协议（12 项收敛清单、提问规则、六大工况问题库、任务书模板）见
`references/brainstorm-protocol.md`，执行要点：

- **触发判断**：关键项有缺 → 进入收敛循环（关键项以协议 §2 表格标 ✦ 的 7 项为唯一口径：
  工况类型、分析目的与关注输出、几何与尺寸、材料、边界约束、初始条件、单位制）；
  信息已齐 → 缺项补默认、标注 `[默认]`，展示任务书一次确认后直接进 §2。
- **收敛循环**（最多 5 轮）：每轮 ≤4 个问题、按"分叉最大优先"（工况→物理→数值）；
  每个问题给 2~4 个带工程默认的选项（Claude Code 用 AskUserQuestion，多问合并一次调用；
  其他环境用编号列表）；用户答"你定"即取推荐值标 `[默认]`。
- **当场量级体检**：用户给的数值立刻按单位制换算核对（密度/模量/速度最容易错），
  矛盾输入（质量与尺寸对不上密度）当轮指出。
- **每轮回显收敛面板**：✅已确认 / 🔶已取默认待认 / ❓下轮要问。
- **确认门（强制）**：任务书展示给用户，问"按此任务书执行？"——这是全流程唯一一次
  强制确认。确认后 spec.md 存入工作目录，进入 §2。
- **无人值守时**（子代理批处理等）：不阻塞，缺项全取推荐默认并逐条标 `[假设]`，
  最终报告里显著提示需人工复核。

单位制速查：`python "SKILL_DIR/scripts/units.py" list`（用户未指定默认 `mm-ton-s` 并声明）。
几何来源：简单几何（板/块/圆柱/球/SPH 填充）由 `gen_mesh.py` 生成；复杂几何请用户
提供含 *NODE/*ELEMENT 的 .k 网格，本技能负责其余全部关键字。

## 2. 资料查找（写卡之前）

查找顺序，从快到慢：

1. **模板**：`SKILL_DIR/templates/<name>/` 每个都在本机 R14.1.1 上跑到过 Normal termination 且过质检。以它为骨架改，不要从零写。

   | 工况 | 模板 | 单位制 | 演示内容 |
   |---|---|---|---|
   | 跌落 | `templates/drop/` | mm-ton-s | 刚体块+重力+初速 砸固支铝板，面面接触 |
   | 碰撞/压溃 | `templates/crash/` | mm-ton-s | 圆管轴向撞刚性墙，自接触折叠，配重 |
   | 侵彻 | `templates/penetration/` | cm-g-us | JC 材料+EOS+侵蚀接触，穿透计算 |
   | 成形 | `templates/forming/` | mm-ton-s | 刚性辊具+位移驱动+质量缩放准静态 |
   | ALE | `templates/ale/` | m-kg-s | S-ALE 溃坝，多物质组+体积填充（能量比门槛放宽至 0.2，S-ALE 对流簿记损耗，NOTES 有量化解释）|
   | SPH | `templates/sph/` | mm-kg-ms | SPH 粒子流冲击结构，粒子-结构接触 |

   每个模板目录的 `NOTES.md` 写明可调参数和验证指标。

2. **材料库**：`knowledge/materials.json`（SI 母库）。取参数一律：
   ```bash
   python "SKILL_DIR/scripts/units.py" material mm-ton-s steel_mild
   ```
   **禁止手抄换算**——单位制错误是最常见也最致命的错误。

3. **官方关键字手册**（R16 Vol I 关键字 / Vol II 材料，共 6000+ 页，已建页码索引）：
   ```bash
   python "SKILL_DIR/scripts/manual_index.py" find MAT_JOHNSON_COOK
   # -> 给出 PDF 路径和页码范围，用 Read 工具的 pages 参数精读
   ```
   **对任何拿不准字段布局的卡片，必须先查手册再写。**
   若本机 Read 工具无法读 PDF（如报 pdftoppm 缺失），用 pypdf 兜底提取文本：
   ```bash
   python -c "from pypdf import PdfReader; r=PdfReader(r'<pdf路径>'); print('\n'.join(r.pages[i].extract_text() for i in range(<起始页-1>,<结束页>)))"
   ```

4. **文献参数检索（只用于物理/经验参数）**：当材料常数、Johnson-Cook/EOS/失效参数、
   摩擦、热参数、应变率或损伤数据需要从论文查找或核验时，使用 bundled
   `academic-search` MCP（来自 `vendor/nature-academic-search/`）。详细边界、证据字段、
   可信度规则见 `references/literature-parameter-routing.md`。
   - 默认工具：`search_papers`、`get_paper_by_id`、`get_citation`、`lookup_mesh`。
   - 默认来源：CrossRef、PubMed、arXiv；Scopus/ScienceDirect 仅在用户本机已配置
     pybliometrics/Elsevier 权限时作为可选来源。
   - 摘要只能用于发现候选文献；采纳数值必须有可访问全文的页码/表格/图/公式来源。
   - 产物写入 `research/parameter-evidence.json`、`research/references.bib`、
     `research/literature-notes.md`。

5. **联网兜底**：dynasupport.com（FAQ/错误号）、dynaexamples.com（算例）、lsdyna.ansys.com。
   本地资料查不到再上网。LS-DYNA 关键字字段、默认值、版本兼容性、官网资料和普通网页搜索
   仍走原路径，不走文献 MCP。

## 3. 生成 k 文件

### 结构与 ID 约定

- 分节组织，每节加横幅注释：`$ ==== CONTROL ====` → DATABASE → MATERIALS → SECTIONS/PARTS → MESH INCLUDES（`*INCLUDE`）→ CONTACT → BOUNDARY/INITIAL → LOADS，最后 `*END`。
- ID 约定：部件 n 取 `PID=SECID=MID=n`；其网格 `nid0=eid0=n*100000`、节点集 `sid0=n*10`；曲线从 901 起；part set 从 801 起。
- 每张数据卡前放 `$#` 字段名注释行。格式细则（固定 10 列、NODE/ELEMENT 特殊列宽、自由格式等）见 `references/kfile-format.md`。

### 必备卡（无一例外）

```
*KEYWORD
*TITLE
*CONTROL_TERMINATION      (ENDTIM)
*CONTROL_ENERGY           (HGEN=2 RWEN=2 SLNTEN=2 RYLEN=2  —— 否则能量质检无数据)
*CONTROL_TIMESTEP         (TSSFAC=0.9；准静态另加 DT2MS 质量缩放)
*DATABASE_GLSTAT          (dt ≈ ENDTIM/200)
*DATABASE_MATSUM          (同上)
*DATABASE_BINARY_D3PLOT   (dt ≈ ENDTIM/20)
*END
```

### 网格生成

```bash
python "SKILL_DIR/scripts/gen_mesh.py" plate --plane xy --origin -75 -75 0 \
    --size 150 150 --div 30 30 --pid 1 --nid0 100000 --eid0 100000 --sid0 10 -o mesh_plate.k
```
子命令：`plate / box / cylinder / cylshell / sphere / sphbox / sphcyl`（圆柱类支持 `--axis x|y|z`）。
输出自带边界节点集（板边/体面/环），stdout 的 JSON 摘要给出 id 范围和集合号——**保存它**，写 SPC/接触时要用。

## 4. 三级验证闭环（核心，逐级通过）

在专用工作目录里跑（deck 同目录会生成一堆结果文件）：

```bash
# L0 静态检查：格式、ID 交叉引用、必备卡——秒级，先过这关
python "SKILL_DIR/scripts/check_kfile.py" model.k
# 必须 0 errors（S-ALE 等求解器生成网格的 "PART has no elements" warning 可接受）

# L1 初始化试算：截短到 50 个循环实跑，专抓初始化错误（材料非法/接触错/引用断）
python "SKILL_DIR/scripts/run_dyna.py" model.k --endcyc 50 --ncpu 4 --timeout 300
# （--endcyc 按循环数截断，无需预估 dt；也可用 --endtim <物理时间>）
python "SKILL_DIR/scripts/parse_results.py" .
# 通过后删除自动生成的 model_trial.k

# L2 全程计算 + 质检
python "SKILL_DIR/scripts/run_dyna.py" model.k --ncpu 4 --timeout 1800
python "SKILL_DIR/scripts/parse_results.py" . --json report.json
```

质检门槛（详见 `references/quality-gates.md`）：Normal termination、零求解器错误、无负体积/飞节点、能量比 0.9~1.1、沙漏能<内能 10%、附加质量<5%（准静态可放宽但须核动能/内能<5%）。

**verdict=FAIL 必须修**：对照 `knowledge/errors.md` 找修法，改完从 L0 重走。最多 8 轮修不好就停下来，把已试过的方案和当前症状如实报告用户。
**修复不许静默偏离任务书**：修复方案若触碰 spec.md 契约项（网格规模、ENDTIM、材料替换、几何简化度等），交互可用时先回用户更新任务书；无人值守时按推荐方案处理并把该项升格为 `[假设]`，在最终报告显著列出。
**verdict=WARN 须解释**：给出量化的物理理由（如侵蚀能带走 8% 能量），写进报告。
**每修复一个新错误**，按 errors.md 底部"经验追加区"的格式追加一行——库会越用越准。
**Final 前强制门**：只要本次任务出现过求解器错误、读卡错误、质检 WARN 修复、或新建模坑并修复成功，就必须先把"症状/原因/修法/日期"追加到 `knowledge/errors.md`，再向用户交付；不得只写入 spec、报告或长期记忆。

MPP 求解（大模型才需要）：`--mode mpp --ncpu 8`；注意 MPP 内存是每进程的。

## 5. 交付报告

最终给用户的内容（缺一不可）：

1. **k 文件**（含 mesh include）路径
2. **验证结论**：termination 状态、能量比、沙漏比、附加质量、单元数、耗时、求解器版本
3. **任务书验收核对**：逐条对照 spec.md 第 6 节验收标准（质检门槛 + 用户关注指标）给出结果
4. **建模假设清单**：单位制、材料参数来源、简化（如刚体化、对称、约束方式）、接触摩擦取值；
   无人值守收敛的 `[假设]` 项显著列出提请复核
5. **可调参数指引**：改速度/尺寸/材料动哪几张卡
6. **文献证据摘要**（如使用文献参数）：列出 `research/parameter-evidence.json`、
   `research/references.bib`、`research/literature-notes.md` 路径，并说明每个采纳参数的
   DOI/页码或表格来源、适用条件和可信度；摘要-only 数值必须标 `unverified`
7. **遗留警告**：质检 WARN 项及其解释；参数可信度提示（文献典型值 ≠ 实测）

## 6. 注意事项

- 带空格路径（本机 `K AGENT`、`Program Files`）在 bash 里必须加引号。
- 并行跑多个求解时每个用 `--ncpu 2`（license 席位共享）；log 出现 license 失败等 60 s 重试。
- 单精度 `sp` 是默认；侵彻/爆炸等大变形对精度敏感时用 `--precision dp` 复核。
- 修改 deck 后重跑前，run_dyna.py 会自动清理旧结果文件；手动跑要注意别解析到陈旧的 glstat。
- 用户提供网格时：先 `check_kfile.py` 单独检查网格文件，确认 PID/节点号范围后再并入。
