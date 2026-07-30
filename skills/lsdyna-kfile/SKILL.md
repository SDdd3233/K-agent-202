---
name: lsdyna-kfile
description: 依据自然语言需求编写完整的 LS-DYNA k 文件（关键字输入卡组），或对用户提供的已有 .k/.key/.dyn deck 进行修改、调试、试算、输出解析和修复验证。覆盖碰撞、跌落、侵彻、成形、ALE、SPH 等显式动力学工况。当用户要求编写/修改/调试/检查 LS-DYNA 模型、k 文件、dyn/key 输入卡组，提到跌落仿真、碰撞仿真、侵彻计算等需求，或只有一个模糊的仿真想法需要梳理成完整方案时使用。
---

# LS-DYNA K 文件编写与自动验证

你的交付承诺：**一份通过本机求解器实际计算验证的完整 k 文件 + 一份验证报告**。
"写完就交"是不允许的——没跑通求解器、没过质检门槛的 deck 不是交付物。

以下把本文件所在目录称为 `SKILL_DIR`。所有脚本在 `SKILL_DIR/scripts/`，
知识库在 `SKILL_DIR/knowledge/`，经过验证的工况模板在 `SKILL_DIR/templates/`。

## 入口路由（先判定）

- **已有 deck 模式**：用户直接提供或明确指向已有 `.k`/`.key`/`.dyn` 主文件，并要求修改、调试、
  跑通、看报错、改参数或修复。跳过 §1 需求头脑风暴、`spec.md` 强制确认、模板适用性判断、
  基准方案门、学术/官方双链路和 §3 从头生成流程；改按 `references/existing-deck-repair.md`
  执行隔离复制 → L0 → L1 → 解析输出 → 诊断 → 最小修改 → 最多 8 轮 → L2 质检。
- **新建 deck 模式**：用户没有提供可作为主 deck 的现有文件，或要求从自然语言/简单几何/网格
  重新构建模型。按 §1~§6 完整流程执行。

已有 deck 模式仍必须做 §0 环境自检、§1.5 历史经验预检、§4 三级验证闭环、§5 交付报告和
Final 前经验追加门。没有 `spec.md` 时，默认契约是“尽量保持原 deck 的物理意图不变，只修复
用户目标范围内的问题”。

## 0. 环境自检（每个新会话第一次使用时做）

```bash
python "SKILL_DIR/scripts/kagent_config.py"    # 检查 4 个求解器 + mpiexec 路径
```

- 默认求解器：`C:\Program Files\ANSYS Inc\v242\ansys\bin\winx64`（LS-DYNA **R14.1.1**）。
  其他机器用环境变量 `LSDYNA_BIN`/`LSDYNA_MPIEXEC` 或 `~/.lsdyna-kagent.json` 覆盖。
- **版本红线：不使用比 R14 新的关键字或字段。** 手册是 R16 版，看到 "R15 及以上" 字样的功能一律回避。
- 手册 PDF 不在时先跑 `python "SKILL_DIR/scripts/fetch_manuals.py"`。

## 1. 需求头脑风暴与收敛 → 《仿真任务书》

用户的输入往往只是一个想法（"我想看看这个件摔了会不会坏"）。本阶段通过**迭代提问**
把它收敛成一份《仿真任务书》（spec.md）——后续建模、验证、交付的唯一契约。
完整协议（12 项收敛清单、提问规则、六大工况问题库、任务书模板）见
`references/brainstorm-protocol.md`，执行要点：

- **触发判断**：关键项有缺 → 进入收敛循环（关键项以协议 §2 表格标 ✦ 的 7 项为唯一口径：
  工况类型、分析目的与关注输出、几何与尺寸、材料、边界约束、初始条件、单位制）；
  信息已齐 → 缺项补默认、标注 `[默认]`，完成 §1.5~§1.6 后展示任务书一次确认，再进 §2。
- **收敛循环**（最多 5 轮）：每轮 ≤4 个问题、按"分叉最大优先"（工况→物理→数值）；
  每个问题给 2~4 个带工程默认的选项（Claude Code 用 AskUserQuestion，多问合并一次调用；
  其他环境用编号列表）；用户答"你定"即取推荐值标 `[默认]`。
- **当场量级体检**：用户给的数值立刻按单位制换算核对（密度/模量/速度最容易错），
  矛盾输入（质量与尺寸对不上密度）当轮指出。
- **每轮回显收敛面板**：✅已确认 / 🔶已取默认待认 / ❓下轮要问。
- **确认门（强制）**：完成模板适用性判断和基准方案选择后，把任务书展示给用户，问
  "按此任务书执行？"——这是全流程唯一一次强制确认。确认后 spec.md 存入工作目录，进入 §2。
- **无人值守时**（子代理批处理等）：不阻塞，缺项全取推荐默认并逐条标 `[假设]`，
  最终报告里显著提示需人工复核。

单位制速查：`python "SKILL_DIR/scripts/units.py" list`（用户未指定默认 `mm-ton-s` 并声明）。
几何来源：简单几何（板/块/圆柱/球/SPH 填充）由 `gen_mesh.py` 生成；复杂几何请用户
提供含 *NODE/*ELEMENT 的 .k 网格，本技能负责其余全部关键字。

## 1.5 历史经验预检（强制，在写卡前）

每次新建或修改 deck，**在选模板、生成网格、写任何关键字卡之前**，必须先读取
`knowledge/errors.md`，并按当前工况、材料、单元类型、接触和关键字检索相关记录。
不得等到 L0/L1/L2 报错后才查。

- 把命中的历史问题转成当前模型的预防检查项，例如字段定宽、单位换算、接触面、刚体约束、
  网格质量、质量缩放和版本兼容性。
- 在 `spec.md` 或建模注释中简要记录已采用的关键预防措施；无相关记录时也要明确标注“已检查，无命中”。
- L0 前逐项核对这些预防检查项；命中记录与当前设计冲突时，先调整 deck，不得带着已知风险进入求解。
- 仅在出现新症状或预检未覆盖的问题时，才在 FAIL 修复阶段再次查询 `knowledge/errors.md`。

## 1.6 基准方案门（强制，任务书确认前）

当工况、分析目标、对象/几何类别和材料类别已经足以形成检索词时，立即读取并执行
`references/brainstorm-protocol.md` §4.4；检索不计入 5 轮提问上限。该子协议是模板适用性、
官方/学术双链路、基准方案选择、`no-similar-case` 与 `M0~M3` 验证阶梯的唯一详细规则来源。

**硬门槛**：

- 模板目录存在不等于模板可用。必须先做模板适用性判定，并把判定结果写入任务书。
- 任一关键维度（物理机制、建模方法、主要载荷/边界、关注输出）不能支撑当前任务骨架时，
  即判定为“无适用模板”。
- 无适用模板时，必须先完成 LS-DYNA 官方资料/官方算例检索和学术文献检索，再给基准方案；
  不得用普通网页搜索、既有经验或相邻模板直接替代该双链路。
- 触发过学术检索时，任务书必须包含文献依据摘要，工作目录必须准备
  `research/literature-evidence.json`；缺少这些证据产物时不得进入写卡阶段。

模板目录速查：

| 工况 | 模板 | 单位制 |
|---|---|---|
| 跌落 | `templates/drop/` | mm-ton-s |
| 碰撞/压溃 | `templates/crash/` | mm-ton-s |
| 侵彻 | `templates/penetration/` | cm-g-us |
| 成形 | `templates/forming/` | mm-ton-s |
| ALE | `templates/ale/` | m-kg-s |
| SPH | `templates/sph/` | mm-kg-ms |

模板适用性判断、无适用模板时的双链路检索、用户明确文献请求和无相似案例处理，均须按该
子协议完成。任务书确认前不写关键字卡；基准方案门完成后才展示任务书并进入唯一确认门。
爆炸焊接、界面波、飞板碰撞、爆轰耦合、热-塑性-失效耦合等高不确定机制若没有专用模板，
默认按“无适用模板”处理。

## 2. 资料补全与写卡前核实

阶段 1 已完成基准方案选择；本阶段只消费任务书并补齐写卡细节，不得无条件重复整轮检索。
如果任务书缺少 §5.1 基准仿真方案、模板适用性判定、官方依据，或触发学术检索后缺少 §8
文献依据/`research/literature-evidence.json`，必须回到 §1.6 补完基准方案门，不得继续写卡。

1. **读取基准**：命中本地模板时读取对应 `NOTES.md`；使用相似/组合方案时按任务书的改造映射
   落实；无相似案例时按任务书中的 `M0~M3` 阶梯构造，禁止跳过最小模型直接拼完整 deck。
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

4. **增量联网补全**：仅当基准方案仍有证据缺口、后续资料与任务书冲突，或用户在本阶段新增
   明确文献要求时联网；具体触发、MCP、查询、去重、证据字段和报告输出均以
   `references/literature-parameter-routing.md` 为唯一规则来源。
   - 文献类输入包括材料/本构/失效/EOS/应变率/热参数、摩擦与界面参数、边界条件、载荷曲线、
     工况和验证算例；学术链路只搜索，不执行引文核对、MeSH 策略、引用文件转换或参考文献管理。
   - 关键字字段、默认值、版本兼容、错误号、求解器行为和官方算例走本地手册/历史经验；仍不足
     时查 dynasupport.com、dynaexamples.com 和 lsdyna.ansys.com。
   - 文献类工程输入不得改用普通网页搜索，求解器专属问题不得改走学术链路；两条链路不可互替。

## 3. 生成 k 文件

### 无相似案例时的受控构造

仅当 `spec.md` 把基准类型标为“第一性原理组合方案”时启用。这里的“从零构建”不是凭经验
一次写完整 deck，而是从官方支持的最小关键字骨架和单机制验证基元逐步集成：

1. **M0 最小模型**：只保留一个主要物理机制、最简几何、已知材料、一个载荷/初始条件和
   必备控制/输出卡；先过 L0 和 L1，确认单位制、时间步和基本运动方向。
2. **M1 材料模型**：用单单元或简化试件验证弹性、塑性、本构、失效/EOS 和单位换算；
   响应趋势或标定点不合理时不得进入下一层。
3. **M2 相互作用**：加入接触、耦合、约束和真实载荷曲线，分别检查穿透、初始间隙、反力、
   能量传递和约束是否符合物理预期。
4. **M3 完整模型**：最后替换为目标几何和网格，逐项合入次要部件与输出请求；每次只增加
   一类复杂度并重跑 L0/L1，全部集成后才执行 L2。
5. **不确定性闭环**：对任务书中没有直接证据的关键参数运行上下界敏感性分析；最终报告
   同时给出参数区间、响应区间和结论是否随假设改变。探索用子模型在 Final 前清理，不得当作
   最终交付 deck。

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

质检判定以 `references/quality-gates.md` 的 G1~G6 为唯一来源；侵彻、S-ALE 和准静态成形的工况例外
也只按该文件判定，并在报告中给出量化说明。

**verdict=FAIL 必须修**：查找LS-DYNA官方资料、关键字手册找修法，改完从 L0 重走。最多 8 轮修不好就停下来，把已试过的方案和当前症状如实报告用户。
**修复不许静默偏离任务书**：修复方案若触碰 spec.md 契约项（网格规模、ENDTIM、材料替换、几何简化度等），交互可用时先回用户更新任务书；无人值守时按推荐方案处理并把该项升格为 `[假设]`，在最终报告显著列出。
**verdict=WARN 须解释**：给出量化的物理理由（如侵蚀能带走 8% 能量），写进报告。
**Final 前强制门**：只要本次任务出现过求解器错误、读卡错误、质检 WARN 修复、或新建模坑并修复成功，
必须按 `knowledge/errors.md` 底部经验追加区记录“症状/原因/修法/日期”，再向用户交付；不得只写入
spec、报告或长期记忆。

MPP 求解（大模型才需要）：`--mode mpp --ncpu 8`；注意 MPP 内存是每进程的。

已有 deck 修复模式必须在隔离工作区运行：

```bash
python "SKILL_DIR/scripts/prepare_existing_deck.py" user_model.k --objective "用户目标"
python "SKILL_DIR/scripts/check_kfile.py" repair_user_model/working/user_model.k
python "SKILL_DIR/scripts/run_dyna.py" repair_user_model/working/user_model.k --rundir repair_user_model/iterations/001 --endcyc 50 --ncpu 4 --timeout 300
python "SKILL_DIR/scripts/parse_results.py" repair_user_model/iterations/001 --json repair_user_model/iterations/001/report.json
```

## 5. 交付报告

最终给用户的内容（缺一不可）：

1. **k 文件**（含 mesh include）路径
2. **验证结论**：termination 状态、能量比、沙漏比、附加质量、单元数、耗时、求解器版本
3. **任务书验收核对**：逐条对照 spec.md 第 6 节验收标准（质检门槛 + 用户关注指标）给出结果
4. **建模假设清单**：单位制、材料参数来源、简化（如刚体化、对称、约束方式）、接触摩擦取值；
   无人值守收敛的 `[假设]` 项显著列出提请复核
5. **文献依据**（触发过文献检索时必填）：按
   `references/literature-parameter-routing.md` 的证据字段分组列出，并给出
   `research/literature-evidence.json` 路径
6. **可调参数指引**：改速度/尺寸/材料动哪几张卡
7. **遗留警告**：质检 WARN 项及其解释；参数可信度提示（文献典型值 ≠ 实测）

## 6. 注意事项

- 带空格路径（本机 `K AGENT`、`Program Files`）在 bash 里必须加引号。
- 并行跑多个求解时每个用 `--ncpu 2`（license 席位共享）；log 出现 license 失败等 60 s 重试。
- 单精度 `sp` 是默认；侵彻/爆炸等大变形对精度敏感时用 `--precision dp` 复核。
- 修改 deck 后重跑前，run_dyna.py 会自动清理旧结果文件；手动跑要注意别解析到陈旧的 glstat。
- 用户提供网格时：先 `check_kfile.py` 单独检查网格文件，确认 PID/节点号范围后再并入。
- Final 前清理工作目录：删除探索、试算、废弃版本等所有不需要的 `.k` 文件，只保留最终主 deck 及其实际 `*INCLUDE` 引用的网格/子模型 k 文件。
