# K 文件格式规范与常用卡片速查

适用求解器：LS-DYNA R14.1.1。字段布局与 R16 手册一致的部分才收录在此；
此处没有的卡片一律 `manual_index.py find <关键字>` 查手册，**不要凭记忆写**。

## 1. 总则

- 关键字行以 `*` 开头、全大写（如 `*CONTROL_TERMINATION`）；`$` 开头是注释行；`*KEYWORD` 开头、`*END` 结尾。
- **固定格式（默认）**：每张数据卡 80 列、8 个字段、每字段 10 列、右对齐。例外见 §2。
- **自由格式**：同一张卡可改用逗号分隔（`0.003, , 0.9`），空字段用连续逗号。两种格式可逐卡混用。列宽拿不准时，宁可用逗号格式，不要写错位的固定格式。
- 空字段只在手册将该字段定义为默认值（例如 "EQ.0"）时才等价于该默认值；显式写 0 与留空
  不得无条件视为等价。
- 数字可用 `1.0E-5` 记法；不要用 Fortran 的 `1.0d-5`。
- `*INCLUDE`：下一行写文件名（相对主 deck 目录）。网格文件用 include 与主 deck 分离。
- 带 `_TITLE` 后缀的关键字：第一张数据卡之前多一行标题文本。带 `_ID` 后缀的接触：第一行是 `CID + 标题`。
- `*PART` 永远有标题行（不需要 _TITLE 后缀）。

## 2. 特殊列宽（最容易错的地方）

| 卡 | 列宽布局 |
|---|---|
| `*NODE` | NID(8) X(16) Y(16) Z(16) TC(8) RC(8) |
| `*ELEMENT_SHELL` | EID(8) PID(8) N1..N8(各8) |
| `*ELEMENT_SOLID`（单行旧格式） | EID(8) PID(8) N1..N8(各8) |
| `*ELEMENT_SPH` | NID(8) PID(8) MASS(16) NEND(8，粒子区间生成用，通常留空) |
| `*ELEMENT_MASS` | EID(8) NID(8) MASS(16) PID(8) |
| `*DEFINE_CURVE` 数据对 | **A(20) O(20)** —— 20 列不是 10 列，经典坑 |
| `*SET_*_LIST` 成员行 | 8 个 id，各 10 列 |

gen_mesh.py 生成的 NODE/ELEMENT/SET 卡已按上表排好，不要手工改动其对齐。

## 3. 常用卡片字段表（10 列字段，按顺序）

### 控制与输出

```
*CONTROL_TERMINATION
$#  endtim    endcyc     dtmin    endeng    endmas     nosol
*CONTROL_ENERGY
$#    hgen      rwen    slnten     rylen          （全部填 2 才有能量明细）
*CONTROL_TIMESTEP
$#  dtinit    tssfac      isdo    tslimt     dt2ms      lctm     erode     ms1st
      （质量缩放: dt2ms 取负值 = 保证最小步长 |dt2ms|，附加质量计入质检）
*DATABASE_GLSTAT / *DATABASE_MATSUM
$#      dt    binary      lcur     ioopt
*DATABASE_BINARY_D3PLOT
$#      dt      lcdt      beam     npltc    psetid
```

### 部件与截面

```
*PART
$ 标题行
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
      （elform: 2=BT 快, 16=全积分抗沙漏；shrf=0.833；金属 nip=5）
*SECTION_SOLID
$#   secid    elform       aet
      （elform: 1=常应力单点积分, 2=全积分；ALE 用 11）
*SECTION_SPH
$#   secid      cslh      hmin      hmax    sphini     death     start   sphkern
      （cslh 默认 1.2；sphkern 核函数默认 0）
```

### 材料（Vol II；密度等数值一律 units.py 换算）

```
*MAT_ELASTIC              (MAT_001)
$#     mid        ro         e        pr        da        db         k
*MAT_RIGID                (MAT_020)
$#     mid        ro         e        pr         n    couple         m     alias
$#     cmo      con1      con2
      （cmo=1 全局约束时 con1/con2 用编码: 0无,1x,2y,3z,4xy,5yz,6zx,7全部；con1 平移 con2 转动。
        cmo 取其他值（局部坐标系/节点约束）时字段含义不同，查手册 MAT_020）
$#（第三张卡整行留空占位）
*MAT_PIECEWISE_LINEAR_PLASTICITY   (MAT_024)
$#     mid        ro         e        pr      sigy      etan      fail      tdel
$#       c         p      lcss      lcsr        vp
$#    eps1 ... eps8       （用 sigy+etan 双线性时 3、4 卡留空行占位）
$#     es1 ... es8
*MAT_JOHNSON_COOK         (MAT_015；实体/2D 连续单元必须配 EOS，壳单元可仅给 E/PR 不配 EOS)
$#     mid        ro         g         e        pr       dtf        vp    rateop
$#       a         b         n         c         m        tm        tr      epso
$#      cp        pc     spall        it        d1        d2        d3        d4
$#      d5      c2/p      erod     efmin    numint
*MAT_NULL                 (MAT_009，流体，需配 EOS)
$#     mid        ro        pc        mu     terod     cerod        ym        pr
*MAT_ADD_EROSION          （附加侵蚀判据；引用已有 mid）
$#     mid      excl    mxpres     mneps    effeps    voleps    numfip       ncs
$#  mnpres     sigp1     sigvm     mxeps     epssh     sigth   impulse    failtm
*MAT_LOW_DENSITY_FOAM     (MAT_057)
$#     mid        ro         e      lcid        tc        hu      beta      damp
$#   shape      fail    bvflag        ed     beta1      kcon       ref
*MAT_MOONEY-RIVLIN_RUBBER (MAT_027)
$#     mid        ro        pr         a         b       ref
$#     sgl        sw        st      lcid
      （a=C10、b=C01 直接给常数时第二张卡留空行占位；用试验曲线拟合时才填 sgl/sw/st/lcid）
```

### 状态方程

```
*EOS_GRUNEISEN
$#   eosid         c        s1        s2        s3     gamao         a        e0
$#      v0
*EOS_LINEAR_POLYNOMIAL
$#   eosid        c0        c1        c2        c3        c4        c5        c6
$#      e0        v0        （理想气体: c4=c5=γ-1, e0=p0/(γ-1)）
```

### 接触（Vol I *CONTACT 章；新手册字段名 SURFA/SURFB 即旧 SSID/MSID）

```
*CONTACT_AUTOMATIC_SURFACE_TO_SURFACE   （_SINGLE_SURFACE 时 surfb 留空）
$#   surfa     surfb   surfatyp  surfbtyp   sboxid    mboxid       spr       mpr
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
$#     sfs       sfm       sst       mst      sfst      sfmt       fsf       vsf
$ 可选 A 卡: soft 等
$#    soft    sofscl    lcidab     maxpar     sbopt     depth     bsort    frcfrq
      （soft=1 罚刚度更稳; 折叠自接触可试 soft=2）
```
surfatyp/surfbtyp（即 SSTYP/MSTYP）编码：0 段集 / 1 壳单元集 / 2 part 集 / **3 单个 part** / 4 节点集 / 5 全模型。
注意：4=节点集只对 surfa 侧有效，surfb 侧不能用 4。
`*CONTACT_ERODING_...` 在 3 张标准卡后多一张：`isym erosop iadj`（推荐 0 1 1）。
`*CONTACT_FORMING_ONE_WAY_SURFACE_TO_SURFACE`：板料作 SURFA，工具作 SURFB。

### 边界、初始条件、载荷

```
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
      （1=约束 0=自由）
*BOUNDARY_PRESCRIBED_MOTION_RIGID   （_SET 时首字段换 nsid）
$#     pid       dof       vad      lcid        sf       vid     death     birth
      （dof: 1x 2y 3z; vad: 0速度 1加速度 2位移）
*INITIAL_VELOCITY_GENERATION
$#      id      styp     omega        vx        vy        vz      ivatn      icid
$#      xc        yc        zc        nx        ny        nz     phase    irigid
      （styp: 1 part集 2 part 3 节点集）
*LOAD_BODY_Z
$#    lcid        sf    lciddr        xc        yc        zc       cid
      （曲线值为正 = 沿 -z 的重力加速度；曲线要覆盖 0~endtim）
*RIGIDWALL_PLANAR
$#    nsid    nsidex     boxid    offset     birth     death     rwksf
$#      xt        yt        zt        xh        yh        zh      fric      wvel
      （xt 尾点在墙面上, xh 头点定法向, 墙挡住法向来流的节点）
*DEFINE_CURVE
$#    lcid      sidr       sfa       sfo      offa      offo    dattyp     lcint
$#                 a1                  o1     （数据对每字段 20 列！）
*SET_NODE_LIST（_TITLE 则先一行标题）
$#     sid       da1       da2       da3       da4    solver
$#    nid1      nid2 ...  （每行 8 个，各 10 列）
*SET_NODE_LIST_GENERATE
$#     sid       da1       da2       da3       da4    solver
$#   b1beg     b1end     b2beg     b2end     b3beg     b3end     b4beg     b4end
      （首末节点号成对，每行最多 4 对；只用 1 对时其余留空）
*SET_PART_LIST
$#     sid
$#    pid1      pid2 ...
```

## 4. 建模惯例（本技能的统一约定）

- 单位制写在 `*TITLE` 和文件头注释里；整个 deck 只用一种单位制。
- 接触优先用 **part 对 part（类型 3）**，省去段集维护；侵蚀接触必须用 ERODING 系列。
- 金属壳 `ELFORM=16, NIP=5`（抗沙漏）；追求速度用 2 但必须盯沙漏能。实体默认 `ELFORM=1` + 必要时 `*HOURGLASS IHQ=6, QM=0.05` 并在 PART 的 hgid 引用。
- 初始几何留接触间隙：壳按中面算，间隙 ≥ 两侧半厚之和；避免初始穿透警告。
- 刚体的约束写在 `*MAT_RIGID` 的 CMO/CON1/CON2 上，**不要**对刚体节点用 SPC。
- 曲线横轴覆盖 0 到 ENDTIM 之外（如 ×2），避免曲线截止导致载荷消失。
- FORMING 类接触的工具面法向必须指向板料：`gen_mesh cylshell` 默认法向朝圆柱内侧，
  作工具时加 `--flip-normal`；d3hsp Warning 40575 显示从节点在 **+side** 才是正常初始间隙。
