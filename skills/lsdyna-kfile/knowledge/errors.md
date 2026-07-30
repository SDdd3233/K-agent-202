# LS-DYNA 常见错误与修复对照表

诊断入口：`python "SKILL_DIR/scripts/parse_results.py" <rundir>` 的 `errors` 列表给出错误号与首行描述；
错误号可用 `python "SKILL_DIR/scripts/manual_index.py" find <关键字>` 配合手册精读。本表按"症状 → 常见原因 → 修法"组织。

## 启动 / license

| 症状 | 常见原因 | 修法 |
|---|---|---|
| `failed to get license` / `License server not responding` / 卡在 license 检查 | 并发席位用尽或网络抖动 | 等 60 s 重试（最多 5 次）；减少并行求解数 |
| 进程秒退、run.log 几乎为空 | 求解器路径错误、非法命令行参数 | `python "SKILL_DIR/scripts/kagent_config.py"` 检查路径；核对 i=/ncpu=/memory= 写法 |
| `memory size ... is insufficient` | memory= 太小 | 提高 memory（如 200m → 500m）；MPP 是"每进程"内存 |

## 初始化阶段（L1 试算就能暴露）

| 症状 | 常见原因 | 修法 |
|---|---|---|
| Error 20019 `Number of processors for decomposition > number of elements` | MPP 进程数超过单元数（极小模型） | 减小 -n 或改用 SMP |
| `... referenced but not defined`（curve/set/part/section/mat） | ID 交叉引用断裂 | 先跑 `check_kfile.py`，它能在不启动求解器的情况下抓住绝大多数此类错误 |
| `input error ... in keyword line` / 读卡错位 | 固定格式列宽错位（字段不是 10 列对齐；NODE 是 8+16+16+16） | 检查该卡片列宽；或该卡整行改逗号自由格式 |
| Warning: initial penetrations | 接触双方几何初始穿透 | 留初始间隙（≥壳厚/2+壳厚/2）；或 CONTACT 卡 IGNORE=1 |
| `part has no elements` | PART 定义了但网格 include 漏了/ PID 不匹配 | 核对 gen_mesh 的 --pid 与 *PART 卡 |
| 质量为 0 / `zero or negative density` | 单位制不一致（如 mm-ton-s 里写了 7850） | 用 `python "SKILL_DIR/scripts/units.py" material <system> <name>` 生成参数，勿手抄 |

## 运行中失稳

| 症状 | 常见原因 | 修法 |
|---|---|---|
| `negative volume in solid element` | 大变形下实体单元翻转（常见于泡沫/软材料、侵彻） | 细化网格；TSSFAC 降到 0.6~0.7；泡沫加 *CONTROL_TIMESTEP 或换 ELFORM=1+沙漏6；侵彻目标加 *MAT_ADD_EROSION（MXEPS 1.5~2.0）让畸变单元删掉 |
| `out-of-range velocities`（shooting nodes） | 接触穿透后弹飞；单位制错；初速方向错 | 查密度/模量单位；接触加 SOFT=1；检查 INITIAL_VELOCITY 方向与数量级 |
| 能量比 total/initial 暴涨（>1.1） | 接触注入能量（穿透+弹开）、质量缩放过猛 | 接触 SOFT=1、降 SLSFAC；DT2MS 减小；检查初始穿透 |
| 能量比骤降（<0.9） | 大量单元侵蚀带走能量（正常）或沙漏耗散过大 | 看 glstat 的 eroded energy 是否解释缺口；否则按下行治沙漏 |
| 沙漏能 > 内能 10% | 单点积分单元 + 弯曲主导变形 | 壳 ELFORM=16（全积分）；体 *HOURGLASS IHQ=6, QM=0.03~0.1 并在 PART 引用；或局部细化 |
| `termination due to mass increase` | 质量缩放增量超限 | DT2MS 绝对值调小；或提高 *CONTROL_TERMINATION 的 DTMIN 判据外放宽 ENDMAS |
| 计算极慢、dt 极小 | 个别畸形小单元控制了全局步长 | d3hsp 搜 "smallest timestep" 定位单元；修网格或用 DT2MS 兜底（注意附加质量门槛） |
| SPH 粒子飞散/不接触 | CSLH 过小、接触没建、粒子与结构用了不同单位制假设 | *CONTROL_SPH 保持默认；接触用 AUTOMATIC_NODES_TO_SURFACE（SPH 部件作 SURFA） |
| ALE 物质泄漏/界面模糊 | 网格太粗、对流方法阶数低 | *CONTROL_ALE METH=2（Van Leer）；加密 S-ALE 网格；检查 AMMG 定义 |

## 质检规则

阈值、工况例外和 WARN 报告要求统一见 `references/quality-gates.md`；本文件只保留错误症状、
原因和修复动作，避免维护第二份质检表。

## 经验追加区（代理每次修复成功后按此格式追加）

<!-- APPEND BELOW: | 症状 | 原因 | 修法 | 日期 | -->
| S-ALE 水/流体模型沙漏能远超内能(比值 >100%) | *MAT_NULL 无剪切刚度, 默认沙漏系数对流体过大; 且水内能极小, 比值分母小 | *HOURGLASS IHQ=1, QM=1e-6~1e-7 并在 PART 引用(手册 MAT_009 Remark 2); QM=1e-5 仍不够时再降一档 | 2026-07-26 |
| S-ALE 溃坝能量比缓降到 ~0.89(无失稳事件) | 多物质对流动量重映不守恒动能, 缺口未入账, 属 Van Leer(METH=2)固有簿记损耗 | 属正常: 门槛放宽 --max-energy-dev 0.2 并在 NOTES 量化(外功-总能=缺口); 严格守恒可换 METH=3 但界面变糊 | 2026-07-26 |
| Error 10087 `*INCLUDE File mesh_*.k does not exist`(文件明明生成过) | run_dyna.py 的 SCRATCH 清理模式含 `mes*`, 把 messag 连同 mesh_*.k 一起删了 | 已改为 `messag*` + `mes[0-9]*`; 若复现: 重新 gen_mesh 后再跑 | 2026-07-26 |
| check_kfile 误报 `SET_NODE 0 ... member nodes missing (first: [11])`(把 sid 当节点) | harvest() 解析 `*SET_NODE_LIST_TITLE` 未跳过标题行, 首行标题被当 sid、sid 行被当数据 | 已修: harvest 里 rows = data[title_or_id_offset(kw, data):] | 2026-07-26 |
| 求解器 warning 21131: IDIM changed from 0 to 3 (CONTROL_SPH) | 固定格式 10 列字段里 1.0000E+20 恰好占满 10 列，前面再留 1 个空格整卡右移错位，IDIM 读成 0 | 满宽(10字符)数值与相邻字段间不留空格，严格按 10 列切分；用 awk length 检查行宽是否 80 | 2026-07-26 |
| ERODING 接触必发 Warning 30364, parse_results 把说明文字里的 "negative volume failure criterion" 误计为负体积失稳事件而 FAIL | parse_results.py 关键词匹配过宽 | 已修 parse_results.py: 排除含 "failure criterion" 的行, 只统计真实的 "negative volume in solid element" | 2026-07-26 |
| 侵彻类单点积分实体 (ELFORM=1) 沙漏比 35%+, 换 IHQ=6 仍 ~10.5-14% (QM 0.05~1.0 全都超) | 高速冲击 + 单点积分固有沙漏; IHQ=6 对该工况不敏感 | 逐组扫描: IHQ=4 (F-B 刚性型) + QM=0.03 降到 9.5% 过关; 侵彻问题沙漏参数必须实测扫描, 别只信"刚性型 0.05"经验值 | 2026-07-26 |
| run_dyna.py --endtim 试算正常, 但之前一次 Error 10087 include 文件找不到 (mesh_*.k 从工作目录消失) | 工作目录曾被外部清理 (SCRATCH glob 不匹配 mesh_*.k, 实测非 clean_rundir 所删); gen_mesh 输出未落盘保存 | 重新生成网格并把 gen_mesh 的 JSON 摘要重定向保存为 mesh_*.json; 复跑前 ls 确认 include 文件在位 | 2026-07-26 |
| check_kfile 对齐规则误报: 报 '0.01.000000E8' 跨界错位, 但 d3hsp 回显读入值完全正确 | 满宽(10列)数值紧贴前一字段是合法固定格式; 旧规则按空白分词只允许"从字段起点整字段打满" | 已修 check_fixed_alignment: 跨界 token 按 10 列切片, 每片是完整数值(不以 . 或 E 开头且可解析)即合法; 判错位以 d3hsp 卡片回显为最终仲裁 | 2026-07-26 |
| FORMING 单向接触工具不推板/穿透, d3hsp Warning 40575 报从节点全在负侧 | gen_mesh cylshell 生成的壳法向朝圆柱内侧, FORMING 类接触对 SURFB 工具面法向敏感 | gen_mesh cylshell/plate 加 --flip-normal 翻转法向(n1n2n3n4→n1n4n3n2); 40575 显示从节点在正侧(+side)才是正常初始间隙 | 2026-07-26 |
| S-ALE 水域重力初始化能量比 total/initial 暴涨(>100), 但动能/速度极小且无失稳 | 真空背景+零表压使初始总能量接近 0, 质检能量比分母失真; 单水层静水压虽可降低扰动, 但初始能量仍偏小 | 改为空气在上、水在下: 空气用 *MAT_NULL + *EOS_LINEAR_POLYNOMIAL(1 atm), 水用 *MAT_NULL + *EOS_GRUNEISEN, 用 *INITIAL_HYDROSTATIC_ALE 定义空气层顶面和水面节点(PBASE=101325 Pa), 同时保留 *LOAD_BODY_Z; 已验证能量比 1.00005 | 2026-07-27 |
