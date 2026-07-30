# forming 模板 — 准静态显式三点辊压成形 (roll bending / 3-point forming)

## 模型说明

刚性圆辊冲头 (R20) 沿 -z 以位移控制把 1.5 mm 厚软钢带压入两个固定支承辊
(R15, 跨距 120 mm) 之间, 冲头行程 25 mm, 总时长 0.02 s。钢带全部节点约束
uy/rotx/rotz, 近平面应变。属于准静态显式成形类模板: 位移控制 + 质量缩放 +
分时段质量阻尼把有效变形阶段的平均动能/内能比压到 5% 以下。

- 求解器: LS-DYNA R14.1.1 (ANSYS 2024R2), SMP 单精度, ncpu=2
- 验证日期: 2026-07-26

## 单位制

mm-ton-s (力 N, 应力 MPa, 能量 mJ, 密度 ton/mm^3)。

## 部件与 ID 表

| PID/SECID/MID | 部件 | 材料模型 | 网格 | nid0/eid0 | 节点集 |
|---|---|---|---|---|---|
| 1 | 钢带 200x40x1.5 | MAT_024 steel_mild (E=210 GPa, sigy=235, ETAN=1200) | plate 80x16 壳, ELFORM=16, NIP=5 | 100000 | 11-15 (边), 18 (全部, SPC 用) |
| 2 | 冲头辊 R20, 轴向 y | MAT_020 刚体, CMO=1 CON1=4 CON2=7 (仅允许 z 平移) | cylshell 48x12, ELFORM=2, T=0.5 | 200000 | 25/26 (端环) |
| 3 | 左支承辊 R15 @ x=-60 | MAT_020 刚体, CON1=7 CON2=7 全固定 | cylshell 36x12 | 300000 | 35/36 |
| 4 | 右支承辊 R15 @ x=+60 | MAT_020 刚体, 同上 | cylshell 36x12 | 400000 | 45/46 |

载荷曲线: 901 = 冲头位移-时间 (201 点); 902 = 钢带质量阻尼常数-时间。
几何: 冲头底缘 z=+1.5 (与板面净隙 0.5 - 两侧壳厚补偿后实际首触约 2 ms);
支承辊顶缘 z=-1.5 (与板底净隙 0.5)。

注意: 三个工具网格的壳单元连接顺序在生成后做了翻转 (n1n2n3n4 -> n1n4n3n2),
使法向从圆柱面指向外侧 (指向钢带)。gen_mesh.py cylshell 生成的原始法向朝内,
FORMING 类接触对 SURFB 段法向敏感 (d3hsp Warning 40575 显示所有从节点在负侧
即为反向信号), 复用网格生成命令时必须重复这一翻转。

## 接触

3 个 *CONTACT_FORMING_ONE_WAY_SURFACE_TO_SURFACE, SURFA=1(板, 按 PID,
SURFATYP=3), SURFB=2/3/4, FS=FD=0.12, VDC=20 (法向接触阻尼 20% 临界,
抑制成形中的接触振铃)。

## 载荷与阻尼 (准静态的关键)

- 冲头运动: *BOUNDARY_PRESCRIBED_MOTION_RIGID pid=2 DOF=3 VAD=2 (位移控制),
  曲线 901: 3 ms 半余弦软着陆 (触板速度 ~0.23 m/s), 之后二次抛物线加速到
  -25 mm (速度随成形抗力增长, 全程 KE/IE 最低)。
- *DAMPING_PART_MASS 仅作用于钢带 (曲线 902): 基础 2000/s (~2/3 倍钢带一阶
  弯曲模态 ~250 Hz 的临界阻尼), 在 7.8-10.2 ms 弹塑性突跳窗口抬到 8000/s、
  10.2-12.2 ms 4000/s。该窗口对应板在冲头下形成塑性铰、弹性弯曲能突然释放
  的时刻; 无阻尼时该瞬间 KE/IE 可达 5+。
- 质量缩放 DT2MS=-4.0e-7 (从规格值 -6e-7 下调, 附加质量从 78% 降到 9.4%;
  加质量阻尼后步长天然高于目标, 附加质量实际为 0%)。

## 关键可调参数

- 行程/速度: 改曲线 901 (由 build_deck.py 的 disp(t) 重新采样; 保持"软着陆 +
  平滑主行程", 触板速度 < ~0.3 m/s)。行程改变后, 阻尼曲线 902 的突跳窗口
  (当前 7.8-12.2 ms) 要对应移到"冲头压深 ≈ 3-6 mm"的时段。
- 板厚: SECTION_SHELL 1 的 T1-T4; 同时重排工具 z 向位置保持 0.5 mm 初始间隙。
- 板长宽/网格密度: 重跑 gen_mesh plate (--size/--div), 节点集 18 的范围
  100000..100000+(na+1)(nb+1)-1 要同步改。
- 材料: `python "SKILL_DIR/scripts/units.py" material mm-ton-s <name>` 生成 MAT_024 参数替换; 屈服强度改变
  后突跳时刻会移动, 复核 glstat 的 KE/IE。
- 摩擦: 接触卡 FS/FD。
- 更快的模拟: 同比例缩短曲线 901/902 的时间轴并减小 ENDTIM; KE/IE 比值会
  随速度平方恶化, 需重新核对 < 5%。

## 验证指标 (parse_results report.json + glstat 复核)

- termination: normal, 46297 cycles, 耗时 ~28 s (2 SMP 线程)
- energy_ratio_final = 1.00007 (max dev 0.016)
- hourglass_over_internal = 0.0 (钢带 ELFORM=16 全积分无沙漏)
- added_mass_pct_max = 0.0% (门槛 25%; 质量阻尼使实际步长高于 DT2MS 目标)
- 单元数: 2720 壳 (板 1280 + 冲头 576 + 支承辊 2x432), 节点 2937
- 准静态核对 (glstat 数值, 取 IE > 5% 终值内能的区间):
  - 全局 KE/IE 峰值 0.095 (t=8.7 ms, 弹塑性突跳瞬间, 单点), 其余仅 2 个采样点
    略超 0.05 (0.062/0.053); 按钢带单件 (matsum) 计 KE/IE 峰值 0.088, 有效变形阶段
    均值 0.018 << 5%, 终值 0.0004。突跳单点是塑性铰形成的物理瞬态, 能量平衡
    1.000 且立即衰减；按 `quality-gates.md` 的准静态例外记录为条件通过，报告该峰值和统计口径。
  - 冲头动能是刚体给定运动携带的, 不计入变形动能。
- d3hsp Warning 40575 (surfa side interface #1-3): FORMING 单向接触初始化时
  报告从节点全部位于工具段正侧 (+ side, 距离 0.9-3.0 mm), 即初始间隙的正常
  提示, 非错误。

## 复现

工作目录下 build_deck.py 为主 deck 生成器 (含曲线 901/902 的解析表达式);
网格由 gen_mesh.py 生成后翻转工具壳法向 (见上)。逐级验证:
check_kfile -> run_dyna --endtim 6e-5 (L1) -> run_dyna 全程 (L2) ->
parse_results --max-added-mass 25。
