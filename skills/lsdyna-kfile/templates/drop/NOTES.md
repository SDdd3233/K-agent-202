# drop — 刚性块跌落冲击铝板模板

## 模型说明
刚性钢块 (40×40×20 mm) 底面距板面 5 mm, 以初速 4 m/s (vz = -4000 mm/s, 约等效 0.8 m 自由跌落) 竖直砸向四边固支的铝板 (150×150×2 mm), 全程含重力。钢块只允许 z 向平移 (CMO=1.0, CON1=4 约束 x/y 平移, CON2=7 约束全部转动), 保证竖直下落不偏摆。求解 3 ms, 覆盖完整"下落-冲击-回弹"过程 (接触约在 t≈1.15 ms 开始, 板内能峰值在 t≈1.75 ms, 之后钢块回弹)。

## 单位制
mm-ton-s: 长度 mm, 质量 ton, 时间 s, 力 N, 应力 MPa, 密度 ton/mm3, 重力加速度 9810 mm/s2。

## 部件与 ID 表
| 部件 | PID=SECID=MID | 网格 nid0/eid0 | 节点集 | 说明 |
|---|---|---|---|---|
| 铝板 | 1 | 100000 | 11~15 (15=四边全部) | 900 壳单元, ELFORM=16, NIP=5, T=2.0 |
| 钢块 | 2 | 200000 | 21~26 (盒面) | 32 六面体, ELFORM=1 |
| 重力曲线 | LCID 901 | - | - | (0, 9810), (1.0, 9810) 常值 |

## 网格与材料
- 铝板: gen_mesh plate --plane xy --origin -75 -75 0 --size 150 150 --div 30 30 (5 mm 网格)。材料 aluminum_6061t6 → *MAT_PIECEWISE_LINEAR_PLASTICITY (RO=2.7e-9, E=68900, PR=0.33, SIGY=276, ETAN=600)。
- 钢块: gen_mesh box --origin -20 -20 5 --size 40 40 20 --div 4 4 2。材料 steel_rigid → *MAT_RIGID (RO=7.85e-9, E=210000, PR=0.3; E/PR 仅用于接触罚刚度)。块质量 = 40×40×20×7.85e-9 = 2.512e-4 ton (251 g)。
- 边界: *BOUNDARY_SPC_SET 节点集 15 (板四边) 全 6 自由度固支。
- 接触: *CONTACT_AUTOMATIC_SURFACE_TO_SURFACE, SURFA=part2 SURFB=part1 (SSTYP 均为 3), FS=FD=0.2, 可选卡 A SOFT=1。
- 重力: *LOAD_BODY_Z 引曲线 901 (正值 9810 即 -z 向重力), 作用于全模型。

## 关键可调参数
- 冲击速度: *INITIAL_VELOCITY_GENERATION 第 1 卡 VZ 字段 (现 -4000 mm/s)。等效跌落高度 h(mm) → vz = -sqrt(2×9810×h)。
- 落差间隙: gen_mesh box 的 --origin 第三个分量 (现 5, 即块底面 z=5 mm)。改动后须同步考虑空程时间 (5 mm / 4000 mm/s ≈ 1.15 ms 含重力加速) 与 ENDTIM。
- 板尺寸/厚度: gen_mesh plate 的 --size/--div 改平面尺寸与网格密度; 厚度改 *SECTION_SHELL 的 T1~T4。
- 块尺寸: gen_mesh box 的 --size/--div; 密度在 *MAT_RIGID 的 RO (决定冲击质量)。
- 材料: 用 `python "SKILL_DIR/scripts/units.py" material mm-ton-s <名称>` 生成参数替换 MID=1 的卡, 禁止手抄换算。
- 仿真时长: *CONTROL_TERMINATION 的 ENDTIM (现 3.0e-3 s); 输出间隔 *DATABASE_GLSTAT/MATSUM 的 DT=1.5e-5, D3PLOT DT=1.5e-4。注意该卡为 10 字符定宽: ENDTIM 必须恰好占满第 1~10 列, 否则后续 ENDENG/ENDMAS 会整体错位被误读 (见下"修订记录")。

## 修订记录
- 2026-07-26: 修复 *CONTROL_TERMINATION 定宽错位。原第 1 字段 ENDTIM 只占 9 字符, 后续字段左移 1 列, 求解器实际读入 ENDENG=0.01 (0.01% 能量比变化即终止的隐藏判据被意外激活)、ENDMAS=0.0 (丢失默认 1e8)。修正为 ENDTIM='    3.0E-3' (10 字符) 并显式写 ENDENG=0.0、ENDMAS=1.0E8; 修复后 d3hsp 回显 'percent change in energy ratio for termination. 0.0000E+00' 与 'percent change in total mass for termination... 0.1000E+09', 与卡面意图一致。check_kfile.py 已同步新增 10 列定宽错位检查规则 (token 跨字段边界即报 ERROR)。

## 验证指标 (2026-07-26 修复后复跑, LS-DYNA R14.1.1 ANSYS 2024R2, SMP sp, --ncpu 2)
- termination: normal (t = 3.0 ms 完整跑完, 终止判据仅 ENDTIM; d3hsp 确认 ENDENG=0, ENDMAS=1e8)
- energy_ratio_final = 1.002 (最大偏差 0.7%, 门槛 0.9~1.1)
- hourglass_over_internal = 0.0 (壳 ELFORM=16 全积分, 无沙漏)
- 附加质量 = 0 (无质量缩放, d3hsp "number of parts with added mass = 0")
- 单元数: 900 壳 + 32 体 = 932; 节点 1036
- 耗时: 约 2.7 s / 3568 循环
- 物理合理性: 初始动能 2010 N·mm (= ½×2.512e-4×4000² = 2010, 精确吻合); 冲击中板内能峰值 1963 N·mm (t≈1.75 ms), 回弹后动能恢复 1943 N·mm, 能量守恒良好。
