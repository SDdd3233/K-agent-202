# crash — 薄壁圆管轴向压溃模板

## 模型说明
薄壁圆管(半径 30 mm, 高 120 mm, 壁厚 1.5 mm)底端置于刚性墙上方(管底 z=1, 墙面 z=0.5),
管顶环节点带 20 kg 集中配重, 整体以 10 m/s 轴向(-z)撞向刚性墙, 发生渐进折叠压溃。
管顶环节点约束 x/y 平移及全部转动(仅 z 平移自由), 模拟落锤导向。约 4 ms 内压溃约 40 mm,
92% 初始动能转化为管壁塑性内能。

## 单位制
mm-ton-s (长度 mm, 质量 ton, 时间 s; 力 N, 应力 MPa, 能量 mJ)。

## 部件与 ID 表
| 部件 | PID=SECID=MID | 网格 | nid/eid 基数 | 节点集 |
|---|---|---|---|---|
| 圆管(壳) | 1 | cylshell 48x40, 1920 壳元 | 100000 | sid=15 底环, sid=16 顶环(48 节点) |

其他 ID:
- 刚性墙: *RIGIDWALL_PLANAR (无 ID 卡), 平面过 (0,0,0.5), 法向 +z, FRIC=0.3
- 配重: *ELEMENT_MASS eid 300001–300048, 每节点 4.1667e-4 ton, 合计 0.02 ton
- 自接触: *SET_PART_LIST sid=801; *CONTACT_AUTOMATIC_SINGLE_SURFACE_ID cid=1, FS=FD=0.2, SOFT=1
- 接触 ID 卡使用 _ID 选项; 载荷曲线未用(初速用 *INITIAL_VELOCITY_GENERATION)

## 网格与材料
- 网格: `gen_mesh.py cylshell --center 0 0 --z0 1 --radius 30 --height 120 --div 48 40
  --pid 1 --nid0 100000 --eid0 100000 --sid0 10 -o mesh_tube.k`
  (1968 节点, 1920 四边形壳元; 周向 48 份, 轴向 40 份)
- 材料: steel_mild (Q235 级) → *MAT_PIECEWISE_LINEAR_PLASTICITY (MAT_024) 双线性:
  RO=7.85e-9, E=2.1e5, PR=0.3, SIGY=235, ETAN=1200 (由 `units.py material mm-ton-s steel_mild` 生成)
- 壳单元: *SECTION_SHELL ELFORM=16 (全积分, 压溃折叠必须, 否则沙漏能超标), NIP=5, T=1.5

## 关键可调参数
- **撞击速度**: *INITIAL_VELOCITY_GENERATION 卡 VZ 字段 (现 -1.000E4 = 10 m/s;
  mm-ton-s 中 1 m/s = 1000 mm/s)。同时按动能调整 ENDTIM。
- **配重质量**: *ELEMENT_MASS 每行 MASS 字段 = 总质量(ton)/48。改配重后总动能变化,
  ENDTIM/压溃行程也要相应调整。
- **管尺寸**: 重跑 gen_mesh cylshell 改 --radius/--height/--div (保持 --z0 1 与刚性墙间隙
  0.5 mm ≥ 半壁厚 0.75 会有轻微初穿透警告, 现用 z0=1 墙面 z=0.5 间隙 0.5, 接触对象是墙,
  RIGIDWALL 不查壳厚, 无穿透问题); --div 周向≥48 保证折叠波长分辨率。改 --height 后若顶环
  节点数变(--div 第一个数), 需重生成 *ELEMENT_MASS 块(顶环节点 = nid0+nc*nz .. nid0+nc*(nz+1)-1)。
- **壁厚**: *SECTION_SHELL T1..T4; 更厚的管压溃力上升, 压溃行程缩短。
- **材料**: `python units.py material mm-ton-s <名>` 重新生成 *MAT 卡参数, 勿手抄换算。
- **接触**: 能量比异常(>1.1)时把 Optional Card A 的 SOFT 由 1 改 2 (段对段)。
- **终止时间**: *CONTROL_TERMINATION ENDTIM (现 4.0e-3 s, 压溃约 40 mm)。

## 验证指标 (2026-07-26, LS-DYNA R14.1.1 ANSYS 2024R2, smp/sp, --ncpu 2)
- termination: normal (9469 cycles)
- energy_ratio_final: 0.9933 (|dev| 0.7%, 门槛 ±10%)
- hourglass/internal: 0.0 (ELFORM=16 全积分, 无沙漏)
- 质量缩放附加质量: 0% (DT2MS=0, 未用质量缩放)
- 单元数: 1920 壳 + 48 质量元; 节点 1968
- 初始动能 1.013e6 mJ → 终态内能 9.29e5 mJ (92% 吸能), 刚性墙终态法向力 3.9e4 N
- 耗时: 8.2 s (L2 全程 4 ms)
- 质检: parse_results 默认门槛 PASS, 0 errors 0 warnings

## 已知注意点
- 压溃折叠对沙漏极敏感: 单点积分壳(ELFORM=2)会导致沙漏能 >10%; 本模板用 ELFORM=16
  沙漏能恒为 0, 代价是每单元耗时约 2-3 倍, 本规模下可忽略。
- 固定格式字段严格 10 列: `4.000E-3` 这类数写成 `  4.000E-3` (共10字符), 多一个空格即错位。
