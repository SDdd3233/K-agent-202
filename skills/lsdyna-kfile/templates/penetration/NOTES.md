# penetration 模板说明

## 模型说明
4340 钢圆柱弹丸以 800 m/s (0.08 cm/us) 沿 -z 方向垂直撞击并**穿透** 2024-T3 铝合金靶板。
靶板四个侧面固支, 弹底与靶顶面留 0.05 cm 初始间隙。接触采用 ERODING_SURFACE_TO_SURFACE,
靶板由 Johnson-Cook 损伤 (D1-D5) + *MAT_ADD_EROSION (等效塑性应变 1.5 兜底) 侵蚀失效,
弹丸穿出后残余速度约 567 m/s (matsum 末帧 part 2 z-rbv = -5.67E-2 cm/us), 全程共侵蚀 154 个单元。

## 单位制
cm-g-us: 长度 cm, 质量 g, 时间 us; 应力/模量 Mbar (1 Mbar = 100 GPa), 速度 cm/us (1 cm/us = 10 km/s),
密度 g/cm3, 比热 Mbar*cm3/(g*K)。ENDTIM=30 us。

## 部件与 ID 表
| 部件 | PID=SECID=MID | EOSID | 网格文件 | nid0/eid0 | 节点集 |
|---|---|---|---|---|---|
| 铝靶板 4x4x0.6 cm | 1 | 1 | mesh_target.k | 100000 | 11/12/13/14 = xmin/xmax/ymin/ymax 侧面 (全固支), 15/16 = zmin/zmax 面 (自由) |
| 钢弹丸 r=0.4 h=1.2 cm | 2 | 2 | mesh_projectile.k | 200000 | 25/26 = 弹底/弹顶面 (未使用) |

HGID=1 (*HOURGLASS 共用), 接触 ID=1。无载荷曲线。

## 网格与材料
- 靶板: gen_mesh `box --origin -2 -2 -0.6 --size 4 4 0.6 --div 24 24 4`, 2304 个六面体, 靶顶面 z=0。
- 弹丸: gen_mesh `cylinder --center 0 0 --z0 0.05 --radius 0.4 --height 1.2 --div 3 6`, 216 个六面体 (方转圆映射全六面体)。
- 总计 2520 单元 / 3468 节点, 两部件均 *SECTION_SOLID ELFORM=1 (单点积分)。
- 材料全部由 `python "SKILL_DIR/scripts/units.py" material cm-g-us <name>` 生成, 禁止手抄:
  - Part 1: `aluminum_2024t3_jc` → *MAT_JOHNSON_COOK (VP=1, A=3.69E-3, B=6.84E-3, n=0.73, C=8.3E-3, m=1.7,
    Tm=775 K, Tr=293 K, EPS0=1E-6 /us, CP=8.75E-6, D1-D5=0.13/0.13/-1.5/0.011/0) + *EOS_GRUNEISEN (C=0.5328, S1=1.338, γ0=2.0, a=0.48)。
  - Part 2: `steel_4340_jc` → *MAT_JOHNSON_COOK (A=7.92E-3, B=5.1E-3, n=0.26, C=0.014, m=1.03,
    Tm=1793 K, D1-D5=0.05/3.44/-2.12/0.002/0.61) + *EOS_GRUNEISEN (C=0.4569, S1=1.49, γ0=2.17, a=0.46)。
- *MAT_ADD_EROSION 挂在 MID=1: EFFEPS=-1.5 (负号 = 按**等效塑性应变** 1.5 失效, 正值是总有效应变, 见手册 Vol II p.2-82)。
- *HOURGLASS IHQ=4 (Flanagan-Belytschko 刚性型) QM=0.03, 两部件共用。这是扫描 IHQ=2/3/4/5/6, QM=0.01~1.0
  后唯一使沙漏比 <10% 的组合 (侵彻类单点积分实体沙漏能天然偏高)。

## 接触
*CONTACT_ERODING_SURFACE_TO_SURFACE: SURFA=2(弹) SURFB=1(靶), SSTYP=3 (按 part ID), FS=FD=0.1;
第 4 张卡 (ERODING 类必需, 位于可选卡 A 之前): ISYM=0 EROSOP=1 IADJ=1; 可选卡 A: SOFT=1。
注意: ERODING 接触自动对全模型实体单元开启负体积失效判据 (Warning 30364, 属正常提示)。

## 关键可调参数
- **撞击速度**: *INITIAL_VELOCITY_GENERATION 的 VZ (现 -0.08 cm/us = 800 m/s; 1 cm/us = 10 km/s)。
- **靶厚**: 重新生成网格 `gen_mesh box --origin -2 -2 -<厚> --size 4 4 <厚> --div 24 24 <层数>` (保持靶顶面 z=0, 每层约 0.15 cm); 弹丸 z0 间隙不变。
- **弹丸尺寸**: `gen_mesh cylinder --radius r --height h --div nr nz`, nr 为半径向单元数。
- **材料**: `python "SKILL_DIR/scripts/units.py" material cm-g-us <名>` 重新生成两张卡, 同时更新 EOS; 材料名见 `SKILL_DIR/knowledge/materials.json`。
- **侵蚀阈值**: *MAT_ADD_EROSION EFFEPS (现 -1.5)。放宽 (更负) → 靶板更难删单元, 更接近纯 JC 损伤控制; 收紧 (~-1.0) → 网格畸变更少但侵蚀能占比升高。
- **求解时长**: ENDTIM (现 30 us, 弹丸 800 m/s 穿 0.6 cm 靶 + 飞离足够)。

## 验证指标 (LS-DYNA R14.1.1, ANSYS 2024R2, SMP sp, --ncpu 2, 2026-07-26)
- termination: normal termination @ t=30 us
- energy_ratio_final = 1.00176 (max dev 0.0022, 门槛 0.15)
- **energy ratio w/o eroded = 0.7491**: 与 1 的缺口 25.1% 恰为 154 个被侵蚀单元带走的
  能量 (matsum 末帧 eroded_ie+ke+hg 合计 3.77E-3, 即初始动能 1.4937E-2 的 25.3%), 物理自洽;
  含侵蚀能的总能量比保持 ~1.00, 无接触注能。
- hourglass/internal = 9.51% (<10% 门槛)
- 附加质量: 无质量缩放 (DT2MS=0), 附加质量 0%
- 单元数 2520 (靶 2304 + 弹 216), 节点 3468
- 全程耗时 ~1.7 s (552→334 cycles, dt 由侵蚀接触控制)
- 弹丸残余速度 ~567 m/s, 穿透确认
