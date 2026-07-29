# K-agent

[![许可证：MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI%20Codex-skill-412991)](https://github.com/openai/codex)

> 把仿真想法变成经过检查、求解器试算并附带验证说明的 LS-DYNA `.k` 文件。

K-agent 是一个 local-first 的智能体技能包和 Claude Code 插件，面向需要稳定、可复用 LS-DYNA 关键字文件工作流的工程团队。它把需求收敛、关键字/手册查询、单位感知的材料选取、网格生成、静态检查、求解器运行和结果质检门槛串成一条流水线。

[English README](README.md)

## 它能做什么

- 把不完整的仿真想法收敛成可审阅的《仿真任务书》。
- 覆盖跌落、碰撞、侵彻、成形、ALE 和 SPH 等工况的完整关键字文件编写。
- 使用内置模板、材料库和 R16 关键字手册索引，同时以文档化的 R14.1.1 求解器基线为目标。
- 自动生成板、块、圆柱、球和 SPH 等简单几何网格；复杂几何可接收用户提供的网格 include。
- 执行 L0 静态检查、L1 初始化试算和 L2 全程计算，检查能量、沙漏、质量缩放和终止状态。
- 需要文献参数时通过内置 `academic-search` MCP 检索，并记录参数证据。

## 为什么需要它

写出语法正确的关键字文件，不等于得到有用的仿真。真正容易出错的地方通常是隐含假设、单位换算、卡片定宽对齐、接触设置、求解器启动错误和结果解释。K-agent 要求这些决策显式化，并把验证轨迹和生成文件放在同一套工作流中。

## 使用前后

| 没有稳定工作流 | 使用 K-agent |
| --- | --- |
| 模糊需求直接变成一份充满隐含假设的大文件。 | 先收敛任务书，并标出所有假设。 |
| 材料值和单位靠手工复制。 | 从单位感知材料库中取值并换算。 |
| 只做肉眼检查就交付。 | 把静态检查和求解器试算纳入交付门槛。 |
| 后续难以追溯文献参数。 | 可记录 DOI、页码/表格、条件和可信度。 |

## 快速开始

### 环境要求

- Python 3.8+。
- 本机 LS-DYNA，才能执行 L1/L2 求解器验证；默认目标是 ANSYS 2024R2 / LS-DYNA R14.1.1。
- `uv`，用于内置文献检索 MCP。核心技能和静态检查不需要 API key。
- 可选：`pypdf`，用于在手册未随包提供时重建关键字手册索引。

### 安装到 OpenAI Codex CLI

```bat
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
install-codex.cmd
```

之后显式调用 `$lsdyna-kfile`，或直接描述 LS-DYNA 建模需求让技能自动激活。

macOS、Linux 或 Git Bash：

```bash
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
bash install-codex.sh
```

### 安装到 Claude Code

开发或本地使用时，可以直接加载插件目录：

```bash
claude --plugin-dir "/path/to/K-agent"
```

也可以添加本地 marketplace 后安装 `lsdyna-kagent`。插件级 `.mcp.json` 会注册内置的 `academic-search` 服务。

### 配置求解器

设置 `LSDYNA_BIN`，MPP 计算还可设置 `LSDYNA_MPIEXEC`；也可以创建 `~/.lsdyna-kagent.json`：

```json
{
  "solver_bin": "C:\\LSDYNA\\bin",
  "mpiexec": "C:\\Program Files\\Microsoft MPI\\Bin\\mpiexec.exe"
}
```

如果官方手册不在本地，执行以下命令下载并建立索引：

```bash
python skills/lsdyna-kfile/scripts/fetch_manuals.py
```

## 使用示例

> 使用 mm-ton-s 单位制，模拟 1 kg 钢块从 1 m 高度跌落到 2 mm 厚 6061 铝板。铝板四边固支，计算 5 ms，并输出变形和能量曲线。

工作流会选择模板、换算材料参数、生成简单网格、组装 deck，并输出验证报告。如果使用文献参数，还会记录来源和适用性，不会把只有摘要支持的数值默认为已验证值。

## 验证闭环

```text
仿真任务书 -> 资料和模板选择 -> deck 生成
    -> L0 静态检查 -> L1 初始化试算 -> L2 求解器计算
    -> 质检门槛 -> 输出假设和可调参数说明
```

技能目录下的典型命令：

```bash
python scripts/check_kfile.py model.k
python scripts/run_dyna.py model.k --endcyc 50 --ncpu 4 --timeout 300
python scripts/run_dyna.py model.k --ncpu 4 --timeout 1800
python scripts/parse_results.py . --json report.json
```

求解器验证依赖本机安装、许可证和可用的求解器路径。没有求解器时仍可运行 L0 检查和网格生成，但不能声称 L1/L2 已通过。

## 仓库结构

```text
.
├── .claude-plugin/              # Claude Code 插件和 marketplace 清单
├── agents/                      # 可选的建模子代理定义
├── skills/lsdyna-kfile/         # 可移植核心技能
│   ├── SKILL.md                 # 主工作流和交付约定
│   ├── references/              # 协议、格式、路由和质检门槛
│   ├── scripts/                 # 网格、单位、检查、求解和解析
│   ├── knowledge/               # 材料库和错误经验
│   ├── templates/               # 跌落、碰撞、侵彻、成形、ALE、SPH
│   └── vendor/                  # 内置 academic-search 集成
├── install-codex.cmd            # Windows 安装脚本
├── install-codex.sh             # macOS/Linux/Git Bash 安装脚本
└── docs/                        # 发布、安全和贡献说明
```

官方手册 PDF 和自动生成的关键字索引被有意从 Git 中排除。这样可以保持仓库轻量，并让用户在本机按自己的授权和网络条件获取手册。

## 安全与隐私

K-agent 面向本地工程工作流。发布或分享生成文件前，请删除 API key、token、cookie、私有路径、原始聊天、未公开研究、客户数据和专有几何。不要把凭据写入技能包；脚本从环境变量或用户本机配置中读取可选服务设置。

发布前检查清单见 [docs/security-and-publishing.md](docs/security-and-publishing.md)。

## 当前状态

仓库已经可以作为可移植技能包使用。文档化的求解器基线是 LS-DYNA R14.1.1，内置手册参考为 R16。材料值属于文献或手册中的代表性值，正式工程结论应使用项目实测数据替换或标定。

## 后续路线

- 增加更多常见冲击和制造工况模板。
- 改进求解器版本兼容性检查和结果报告移植性。
- 扩展证据适配器，同时保持凭据和私有数据留在本机。
- 为更多关键字卡片增加与求解器无关的小型回归样例。

## 参与贡献

欢迎提交示例、模板、文档和验证改进。请勿提交密钥、专有 deck、私有网格、原始聊天或客户数据。提交 Issue 或 Pull Request 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目采用 [MIT License](LICENSE) 发布。

## 一句话总结

K-agent 是一个 local-first 的 LS-DYNA 编写技能，把自然语言仿真需求变成经过求解器检查、可审计的关键字文件。
