# 固定基线参数化示例

这个目录演示“纯文本 → 白名单参数 → 用户审查 → 固定基线 K 文件 → L0 → 求解提交”的最小链路。
示例 K 文件仅用于演示字段映射和静态门禁，不代表真实工程模型。

```powershell
$scripts = "..\..\scripts"
python "$scripts\parameter_contract.py" extract project.json `
  --text "装填速度为 8 m/s，摩擦系数为 0.12" `
  --out extracted.json --review-out review.md

# 用户核对 review.md 后再执行确认；--reviewer 应写实际审查人。
python "$scripts\parameter_contract.py" confirm project.json extracted.json `
  --reviewer "用户姓名" --out confirmed.json

python "$scripts\build_parameterized_case.py" project.json confirmed.json `
  --out cases\case-001 --case-id case-001

python "$scripts\parameter_case_workflow.py" l0 cases\case-001
python "$scripts\parameter_case_workflow.py" status cases\case-001

# 只有 L0 通过后才可提交。需要先按项目说明配置 LS-DYNA 路径。
python "$scripts\parameter_case_workflow.py" submit cases\case-001 `
  --mode smp --ncpu 4 --timeout 1800
```

把该示例用于真实项目之前，至少需要：

1. 用已经人工验证且可计算的模型替换 `baseline/`；
2. 根据实际可变参数收紧 `parameters` 白名单、单位和上下限；
3. 为每个参数配置准确的 `keyword_mappings`，并保留 `expected` 基线旧值；
4. 用已知输入与已知 K 文件做回归测试，确认每个映射只改变预期字段。
