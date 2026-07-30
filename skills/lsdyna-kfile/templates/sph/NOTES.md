# sph 模板 — SPH 水柱冲击四边固支铝板（简化鸟撞/液滴冲击）

## 模型说明
Ø25×50 mm 的 SPH 水柱以 100 m/s 沿 -z 方向垂直冲击 150×150×3 mm 四边全固支
6061-T6 铝板。水用 *MAT_NULL + *EOS_GRUNEISEN 描述，SPH 粒子与板壳之间用
*CONTACT_AUTOMATIC_NODES_TO_SURFACE (SOFT=1) 耦合。冲击动能转化为板的塑性
变形能与水的内能/飞溅动能，板中心留下永久凹陷。

## 单位制
mm-kg-ms：力 kN、应力 GPa、能量 J (kN·mm)、密度 kg/mm³、速度 mm/ms = m/s。

## 部件与 ID 表
| 部件 | PID=SECID=MID | 网格 | nid0/eid0 | 节点集 |
|---|---|---|---|---|
| 铝板 150×150×3 | 1 | 30×30 壳 (900 单元, 961 节点) | 100000 | 11~14 四条边, 15 全部边界(固支用) |
| SPH 水柱 Ø25×50 | 2 (EOSID=2) | 2688 粒子 | 200000 | 21 全部粒子 |

历史输出节点：100480 = 板中心 (0,0,0)。

## 网格与材料
- 板：`gen_mesh.py plate --plane xy --origin -75 -75 0 --size 150 150 --div 30 30`；
  *SECTION_SHELL ELFORM=16(全积分) NIP=5 T=3.0。
  材料 aluminum_6061t6 (`python "SKILL_DIR/scripts/units.py" material mm-kg-ms aluminum_6061t6`)：RO=2.7e-6, E=68.9, PR=0.33,
  SIGY=0.276, ETAN=0.6 → *MAT_PIECEWISE_LINEAR_PLASTICITY (MAT_024 双线性用法)。
- 水柱：`gen_mesh.py sphcyl --center 0 0 --z0 2 --radius 12.5 --height 50
  --div 6 24 --rho 9.98e-7`；粒子质量约 9.11e-6 kg/粒(脚本按体积分配写入
  *ELEMENT_SPH 第三字段)。z0=2 mm 留初始间隙避免初始穿透。
  *SECTION_SPH CSLH=1.2 其余默认；水参数由 `python "SKILL_DIR/scripts/units.py" material mm-kg-ms water` 生成：
  RO=9.98e-7, MU=1e-9, PC=-1e-5；EOS_GRUNEISEN C=1480 (声速 mm/ms), S1=1.979,
  GAMMA0=0.11, A=3.0, E0=0, V0=1.0。
- *CONTROL_SPH 全默认 (NCBS=1, IDIM=3, NMNEIGH=150, FORM=0)。

## 关键可调参数
- 冲击速度：*INITIAL_VELOCITY_GENERATION 卡 1 的 VZ (现 -100，单位 m/s)。
  改速度后建议同步复核 ENDTIM 是否足以覆盖回弹段。
- 水柱尺寸/分辨率：重新跑 gen_mesh sphcyl 改 --radius/--height/--div
  (nr=半径向粒子数, nz=轴向层数)，务必保留 --rho 9.98e-7 与 --z0 ≥ 2。
  改半径需保证仍落在板内。粒子间距应接近 (radius/nr ≈ height/nz)。
- 板尺寸/厚度：gen_mesh plate 改 --size/--div；厚度在 *SECTION_SHELL T1~T4。
  固支边界自动跟随 (节点集 15 由脚本重生成)。
- 材料替换：`python "SKILL_DIR/scripts/units.py" material mm-kg-ms <名称>` 生成参数后替换 MAT 卡；
  板换钢等更硬材料时挠度显著减小属正常。
- 输出频率：GLSTAT/MATSUM/NODOUT dt=0.0075，D3PLOT dt=0.075，按需缩放。
- 若加大速度出现接触穿透/能量比升高：接触已用 SOFT=1，可再降 SFSA/SFSB 或
  细化板网格。

## 验证指标 (LS-DYNA R14.1.1, smp/sp, --ncpu 2, 2026-07-26)
- termination: normal，ENDTIM=1.5 ms 全程完成，耗时约 6 s，1785 周期
- 能量比 total/initial: 终值 1.005 (最大偏差 0.51%) — PASS
- 沙漏能/内能: 0.0 (壳 ELFORM=16 全积分；SPH 无沙漏) — PASS
- 附加质量: 0% (未用质量缩放, DT2MS=0)
- 单元数: 900 壳 + 2688 SPH 粒子, 3649 节点
- 物理合理性: 初始动能 122.47 J (= 0.5×0.0245 kg×(100 m/s)²，解析吻合)；
  终态动能 67.2 J (水回弹/飞溅)、内能 56.6 J (板塑性 14.1 J + 水压缩 42.5 J)；
  板中心 (节点 100480) 峰值挠度 -4.88 mm @ t=0.36 ms，永久变形约 -1.5 mm；
  动能→内能转化明确，粒子确实撞击板面。

## 已知注意点
- *CONTROL_SPH / *SECTION_SPH 中 1.0000E+20 这类 10 列满宽数与相邻字段之间
  不能再留空格，否则固定格式会错位 (本模板已按 10 列严格对齐)。
- MAT_NULL 的 YM/PR 仅用于接触刚度估计，本模型接触刚度由板侧主导，留 0 即可；
  若接触异常可给水侧 YM≈2.2e-3 (水体积模量量级) 辅助。
