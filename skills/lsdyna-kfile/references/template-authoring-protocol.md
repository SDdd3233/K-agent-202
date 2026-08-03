# K 文件模板制作协议

本协议用于“用户上传一个已有 `.k`/`.key`/`.dyn` 文件，并明确说明它要作为某类模板”的请求。
它与 `references/existing-deck-repair.md` 的目标不同：修复流程交付一个修复后的具体 deck，
本流程交付一个可复用、可验证、边界明确的模板。

## 1. 触发与工作区

### 1.1 触发条件

仅当以下条件同时满足时进入模板制作模式：

1. 用户上传了主 `.k`/`.key`/`.dyn` 文件（以及可用的 `*INCLUDE` 文件）；
2. 用户说明该文件要作为哪一种模板，或说明模板将复用于哪类工况；
3. 用户请求抽象、整理、参数化、沉淀或制作模板。

如果用户只要求修改、调试、运行或诊断该文件，仍走 `existing-deck-repair.md`。
如果用户要求从自然语言重新建模，走新建 deck 流程。

### 1.2 源文件保护与目录

先运行 `prepare_existing_deck.py` 建立证据副本；不得直接编辑上传文件：

```text
template_build/<template-name>/
├── source/                 # 上传文件和 include 闭包，只读
├── analysis/               # 结构化分析、问题清单、参数候选
├── working/                # 待确认的候选模板和生成文件
├── iterations/             # L0/L1/L2 迭代证据
└── validation/             # L0/L1/L2 输出和报告
```

推荐命令为：

```bash
python "SKILL_DIR/scripts/prepare_existing_deck.py" user_model.k \
  --outdir template_build/<template-name> \
  --objective "制作 <模板用途> 模板"
```

`source/` 中的文件是物理意图和来源证据。模板工作只能写入 `working/`，求解器运行只能写入
`validation/`；不得覆盖原始文件或把验证结果写回模板源目录。

## 2. 分析阶段

分析阶段先读取 `knowledge/errors.md`、`references/kfile-format.md` 和现有模板的 `NOTES.md`。
模板目录存在不等于模板适用；必须记录现有模板是否在物理机制、建模方法、主要载荷/边界和关注输出
四项上支撑上传文件与用户声明的用途。

对上传文件建立一份模板候选画像，至少包括：

- 单位制、求解器版本和输入文件的 include 图；
- `*CONTROL`、终止时间、时间步、质量缩放和数据库输出；
- 几何、网格、部件、截面、材料、EOS、接触、边界、初始条件和载荷曲线；
- ID 分配规律、节点集/部件集用途、硬编码参数和绝对路径；
- 可参数化项、参数联动、不可泛化的专用设置；
- 物理意图、关注输出、已知 WARN/FAIL 和验证证据。

先运行静态检查：

```bash
python "SKILL_DIR/scripts/check_kfile.py" source/<main-deck>.k
```

静态检查、文件分析和短时试算只用于发现问题，不等于最终模板已获准交付。

## 3. 关键问题门

### 3.1 只问影响结果的问题

分析过程中发现会改变模板物理、参数接口、适用范围或验收结论的问题，进入关键问题门。问题总数
在整个模板制作请求中不得超过 **5 个**，而不是每轮 5 个。问题应一次集中提出；每个问题必须说明
当前证据、对模板结果的影响，并给出 2~4 个选项，推荐项放在首位。

优先询问：

1. 无法可靠判断的单位制或物理用途；
2. 材料、EOS、失效、侵蚀、接触或边界条件的真实意图；
3. 是否将硬编码尺寸、速度、厚度、摩擦、终止时间等暴露为模板参数；
4. 修复文件错误是否允许改变原始物理意图；
5. 用户关注的输出和模板验收指标。

不要为注释风格、文件命名或可由工具确定的字段反复询问。

### 3.2 问题分类和停止规则

- 可自动处理：字段对齐、注释、相对 include 路径、明显的 ID 冲突、质量门禁所需的常规输出卡。
- 必须询问：单位、物理机制、材料模型/常数、载荷、约束、接触、侵蚀、生产 `ENDTIM`、几何或网格
  拓扑等会改变物理结论的内容。
- 仅报告：不影响模板主结果的简化、可量化的 WARN、已知的适用边界和证据不足。

遇到必须询问的问题时暂停模板抽象和最终验证；用户回答后更新分析记录再继续。达到 5 个问题仍有
未决项时，不再追加问题：采用用户明确授权的推荐默认值并标记 `[默认]`，否则将该项标记为
`[假设]`，缩小模板适用范围并在最终报告中显著说明。无人值守场景沿用新建 deck 流程的
`[假设]` 规则，但不能伪造用户确认。

## 4. 模板契约

关键问题门关闭后，写入 `working/template_spec.md`。契约至少包含：

```text
模板名称和物理类别
适用工况与不适用工况
单位制和求解器版本
必填参数、可选参数、默认值、范围和单位
参数联动与修改后必须重建的文件/集合/曲线
部件、集合、曲线和 include 的 ID 规则
材料和 EOS 来源
预期输出与验收标准
已确认项、[默认]、[假设]、证据缺口和来源 deck 哈希
```

模板参数必须围绕用户用途抽象，而不是把每个输入字段都暴露出来。尺寸、速度、材料、厚度、摩擦、
终止时间和网格密度只有在会改变适用范围或结果时才作为公开参数；由参数派生的节点集、质量、
初始间隙、输出间隔和终止时间必须写出联动关系。

现有模板类别可作为命名和验收参考：

| 类别 | 目录 | 单位制 | 重点输出 |
|---|---|---|---|
| 跌落 | `templates/drop/` | `mm-ton-s` | 接触、回弹、能量、板变形 |
| 碰撞/压溃 | `templates/crash/` | `mm-ton-s` | 吸能、峰值力、折叠、沙漏 |
| 侵彻 | `templates/penetration/` | `cm-g-us` | 穿透、残余速度、侵蚀能量 |
| 成形 | `templates/forming/` | `mm-ton-s` | 减薄、回弹、有效阶段 KE/IE |
| ALE | `templates/ale/` | `m-kg-s` | 流场、压力、流固耦合 |
| SPH | `templates/sph/` | `mm-kg-ms` | 冲击力、结构变形、粒子状态 |

若四项适用性中任一项不能支撑当前用途，不能把相邻模板标为直接基准；必须按新建 deck 流程触发
官方资料/官方算例和学术文献双链路，或将模板标记为 `no-similar-case`。

## 5. 抽象、修复与生成

在用户确认或明确授权默认值后：

1. 保留原始物理机制，抽出契约中的参数，删除绝对路径、临时输出和案例专用命名；
2. 用 `units.py` 生成材料参数，按 `kfile-format.md` 修正固定列宽和特殊卡片；
3. 保留现有模板的 ID 约定；由网格参数派生节点集、部件集、质量元和接触对象；
4. 简单几何优先使用 `gen_mesh.py`，复杂网格保留实际 `*INCLUDE`；
5. 补齐 `*DATABASE_GLSTAT`、`*DATABASE_MATSUM`、`*DATABASE_BINARY_D3PLOT` 等质量门禁所需输出；
6. 写入 `NOTES.md`，说明模型、参数、复现命令、验证指标、已知限制和参数修改联动。

禁止在未确认时更换材料模型、EOS、失效判据、载荷、约束、接触、生产终止时间、网格拓扑或物理简化。

## 6. 验证闭环

模板候选必须重新验证，不能直接沿用来源 deck 的报告：

```bash
python "SKILL_DIR/scripts/check_kfile.py" working/<template>.k
python "SKILL_DIR/scripts/run_dyna.py" working/<template>.k \
  --rundir validation/l1 --endcyc 50 --ncpu 4 --timeout 300
python "SKILL_DIR/scripts/parse_results.py" validation/l1 \
  --json validation/l1/report.json
python "SKILL_DIR/scripts/run_dyna.py" working/<template>.k \
  --rundir validation/l2 --ncpu 4 --timeout 1800
python "SKILL_DIR/scripts/parse_results.py" validation/l2 \
  --json validation/l2/report.json
```

L0 必须无错误；L1 必须能读卡、推进并通过初始间隙、运动方向和时间步检查；L2 按
`references/quality-gates.md` 检查正常结束、零错误、失稳、能量比、沙漏比和附加质量。
还必须确认接触实际发生、关注输出存在且结果与模板用途一致。

至少用来源 deck 的默认参数做一次代表性实例化；参数公开后，再做一次不会改变物理类别的轻微变体，
确认 ID、集合、include、曲线和输出卡不会失配。成形类模板必须另外报告有效变形阶段的 KE/IE；
侵彻、ALE 和 SPH 必须按对应模板的能量解释记录侵蚀或对流簿记影响。

任何 FAIL、WARN 修复或新建模坑修复成功后，按主 skill 的要求追加到 `knowledge/errors.md`。

## 7. 交付物

模板目录采用现有模板的布局：

```text
skills/lsdyna-kfile/templates/<template-name>/
├── <template-name>.k
├── mesh_*.k
├── build_deck.py          # 仅复杂或高度参数化模板需要
├── NOTES.md
└── template_spec.md
```

验证目录至少保留：

```text
runs/template_build/<template-name>/
├── validation_report.md
├── report.json
├── run.log
└── final_delivery_report.md
```

最终交付报告必须列出来源 deck、模板路径、实际 include、参数契约、用户确认项、L0/L1/L2 结果、
适用边界、所有 WARN/FAIL、假设和未完成验证。报告写入并发送前不得结束任务。
