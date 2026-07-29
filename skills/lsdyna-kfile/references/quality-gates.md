# 质检门槛（L2 验收标准）

`parse_results.py` 的 verdict 规则。数据来源：d3hsp / mes* / glstat
（glstat 有能量明细的前提是 deck 里有 `*DATABASE_GLSTAT` + `*CONTROL_ENERGY` HGEN=RWEN=SLNTEN=RYLEN=2）。

## 硬门槛（违反即 FAIL，必须修复）

| 门槛 | 判据 | 说明 |
|---|---|---|
| G1 正常结束 | d3hsp/messag 出现 `N o r m a l  t e r m i n a t i o n` | Error termination / 超时 / 崩溃都算失败 |
| G2 零错误 | 无 `*** Error` | 错误号查 knowledge/errors.md 与手册 |
| G6 无失稳事件 | 无 negative volume / out-of-range velocities / NaN | 出现即物理失稳，结果不可用 |

## 软门槛（违反为 WARN，需给出量化解释或修复）

| 门槛 | 判据 | 超限的典型含义 |
|---|---|---|
| G3 能量平衡 | max\|total/initial − 1\| ≤ 0.10 | 涨→接触注能/质量缩放过猛；跌→侵蚀或沙漏耗散。侵彻类可放宽到 0.15，但要核对 glstat 的 "energy ratio w/o eroded energy" ≈ 1；S-ALE 多物质对流可放宽到 0.2（对流簿记损耗，需在 NOTES/报告量化） |
| G4 沙漏能 | 峰值沙漏能/峰值内能 ≤ 0.10 | 单点积分单元弯曲主导。改 ELFORM=16（壳）或 IHQ=6（体） |
| G5 附加质量 | 质量增加 ≤ 5% | 质量缩放引入。准静态成形可放宽到 ~25%，但必须另核 **动能/内能 < 5%**（glstat 里对比 kinetic/internal energy） |

阈值可用参数覆盖：`parse_results.py . --max-energy-dev 0.15 --max-hourglass 0.10 --max-added-mass 25`。
放宽任何阈值都必须在交付报告里写明理由。

## 常见"正常结束但不可信"的追加自检

- d3plot 数量是否符合预期（求解真的推进到了 ENDTIM）
- 变形模式肉眼合理（LS-PrePost 在求解器同目录的 lsprepost411/ 下，可命令行出图）
- 接触力（rcforc，需 *DATABASE_RCFORC）非零且无高频震荡发散
- 侵彻类：残余速度/穿透深度与经验公式同数量级
