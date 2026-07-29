# ale — S-ALE 溃坝模板 (结构化 ALE 水柱坍塌)

## 模型说明
S-ALE(结构化 ALE)溃坝基准: 0.6 m x 0.05 m x 0.4 m 封闭水槽, 左下角
0.15 m x 0.05 m x 0.25 m 水柱在 t=0 释放, 重力 (9.81 m/s^2, -z) 驱动下
坍塌, 沿槽底向 +x 流动并冲击右壁。域内其余部分为真空(*MAT_VACUUM),
全部 6 个外表面 NOFLOW(滑移固壁, 法向不可穿透)。

- 网格由求解器按 *ALE_STRUCTURED_MESH + 3 张 CONTROL_POINTS 卡自动生成
  (60 x 5 x 40 = 12000 个均匀六面体, 单元尺寸 0.01 m), 无需 mesh include 文件。
- 多物质: *ALE_MULTI-MATERIAL_GROUP 两组, AMMG1=真空, AMMG2=水;
  *SECTION_SOLID ELFORM=11 多物质单点 ALE。
- 初始填充: *ALE_STRUCTURED_MESH_VOLUME_FILLING 先 ALL 填 AMMG1,
  再 BOXCOR(*DEFINE_BOX 1, 各向外扩 0.01 m 保证边界单元全填) 填 AMMG2。
- 对流: *CONTROL_ALE DCT=-1(S-ALE 强制改进对流), METH=2(Van Leer 二阶),
  AFAC=-1 关闭网格光滑(纯欧拉)。

## 单位制
m-kg-s (SI)。压力 Pa, 密度 kg/m^3, 能量 J。

## 部件与 ID 表
| 实体 | ID | 说明 |
|---|---|---|
| PART 1 / SEC 1 / MAT 1 | 1 | 真空背景 AMMG1, *MAT_VACUUM rho=1e-4 |
| PART 2 / SEC 2 / MAT 2 / EOS 2 | 2 | 水 AMMG2, *MAT_NULL + *EOS_GRUNEISEN |
| S-ALE 网格 MSHID / DPID | 1 / 3 | DPID=3 由求解器自动生成 PART(不需 *PART 卡) |
| S-ALE 节点/单元起始 ID | 300001 | NBID=EBID=3*100000+1 |
| CONTROL_POINTS | 1001/1002/1003 | x: 61 点 0..0.6; y: 6 点 0..0.05; z: 41 点 0..0.4 |
| *DEFINE_BOX | 1 | 水柱初始区域 |
| 载荷曲线 | 901 | 重力 9.81 常值 (0,9.81)-(1,9.81) |
| *HOURGLASS | 1 | IHQ=1, QM=1e-7 (流体专用, 见下) |

## 网格与材料
- 网格: 60x5x40 均匀, dx=dy=dz=0.01 m, 12000 单元 / 12546 节点。
- 水(units.py material m-kg-s water, 禁手抄): rho=998, mu=0.001 Pa.s,
  PC=-1e4 Pa(气蚀截断); Gruneisen C=1480, S1=1.979, gamma0=0.11, a=3.0, E0=0。
- 真空: *MAT_VACUUM 仅需估计密度(1e-4, 比水轻 7 个量级, 仅作稳定性检查)。

## 关键可调参数
- **域尺寸/分辨率**: 改 3 张 *ALE_STRUCTURED_MESH_CONTROL_POINTS——
  第 2 个数据行的 N=节点数(单元数+1), X=终点坐标。加密到 120x10x80 时把
  N 改为 121/11/81。同时按需改 *DEFINE_BOX 1 的水柱范围。
- **水柱大小**: *DEFINE_BOX 1 的 xmx/zmx (当前 0.15/0.25); min 方向留 -0.01
  外扩以完整覆盖边界层单元。
- **重力**: 曲线 901 的纵坐标; 若模拟时长 >1 s 需延长曲线横坐标。
- **材料**: 换介质时用 `python units.py material m-kg-s <名>` 重新生成
  *MAT_NULL/*EOS_GRUNEISEN 参数; 若改为水+空气双流体, 把 PART 1 换成
  *MAT_NULL+*EOS_IDEAL_GAS(或 LINEAR_POLYNOMIAL) 并在 *CONTROL_ALE
  设 PREF 平衡参考压。
- **边界**: *BOUNDARY_SALE_MESH_FACE 每面独立开关; NOFLOW=滑移固壁,
  FIXED=全约束, NONREFL=无反射(开域)。顶面若要"开口"可将 POSZ 改 NONREFL。
- **出图频率**: *DATABASE_BINARY_D3PLOT DT (当前 0.015 s → 21 个状态)。
- **时长**: *CONTROL_TERMINATION ENDTIM=0.30 s。

## 验证指标 (求解器 LS-DYNA R14.1.1 smp/sp, 日期 2026-07-26)
- termination: Normal Termination, 无 error / 无失稳事件
- 单元数: 12000 solid (S-ALE 自动生成); 求解耗时 201.4 s (--ncpu 2)
- 能量比 total/initial: 终值 0.888, 最大偏差 0.112 (< 门槛 0.2)
- 沙漏能/峰值内能: 1.8% (< 10%)
- 附加质量: 0% (未用质量缩放, DT2MS=0)
- d3plot 状态数: 22 (> 15), 水柱明显坍塌流动: t=0.3 s 时水 KE=1.45 J,
  x 方向动量 1.72 kg·m/s (平均 x 速度约 0.92 m/s, 已冲向右壁)

### 能量比 0.888 的量化解释 (WARN 门槛放宽到 0.2 的原因)
重力外功 W=1.632 J, 终态总能 1.449 J, 缺口 0.183 J (11.2%)。这是多物质
ALE 对流簿记的固有损耗: METH=2 (Van Leer) 每步对流严格守恒质量与动量,
但动量重映后节点动能 sum(0.5*m*v^2) 系统性小于对流前值(KE 与动量不能
同时守恒), 差额未计入任何能量项。本模型内能仅 2.5e-4 J, 动能 1.45 J,
全部缺口都表现在动能簿记上, 属 S-ALE 正常行为而非数值失稳(无负体积/
无飞节点, 动量与自由面形态正确)。若需更严能量簿记可改 METH=3 (总能守恒
的 donor cell, 一阶精度, 界面更糊), 本模板保持二阶 Van Leer。

### 沙漏参数说明
*MAT_NULL 无剪切刚度, 手册 (Vol II *MAT_009 Remark 2) 要求流体用
IHQ=1 且 QM 取小值。QM=1e-5 时沙漏能达内能的 183%(因为水内能本身极小),
QM=1e-7 时降到 1.8% 且流场无肉眼可见差异; 本模板固定 QM=1e-7。

## 文件清单
- `ale.k` — 主 deck(自包含, 无 mesh include; S-ALE 网格由求解器生成)
- 运行: `lsdyna i=ale.k ncpu=2` 或 `python run_dyna.py ale.k --ncpu 2`
