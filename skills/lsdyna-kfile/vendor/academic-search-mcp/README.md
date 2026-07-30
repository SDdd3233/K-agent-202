# K-Agent Academic Search MCP

K-Agent 内部的 search-only MCP fallback，整合 CrossRef、PubMed、arXiv、
Scopus 和 ScienceDirect。它不是独立 skill，也不提供引文核对、MeSH、
引用文件转换或参考文献管理。

## 工具

| 工具 | 功能 |
|---|---|
| `search_papers` | 默认并发检索 CrossRef、PubMed、arXiv，可显式加入 Elsevier 来源 |
| `search_scopus` | 可选的 Scopus 高级检索 |
| `search_sciencedirect` | 可选的 ScienceDirect 文献检索 |

## 配置

- `PUBMED_EMAIL`：NCBI 要求的联系邮箱。
- `NCBI_API_KEY`：可选，用于提高 PubMed 请求速率。
- Scopus / ScienceDirect：复用本机 `~/.config/pybliometrics.cfg`，仅在
  显式选择对应来源时访问。

安装器优先复用用户已有的 `academic-search` MCP。只有明确确认不存在时，
才用 `uv` 注册本目录中的 fallback；不会覆盖已有命令、路径、环境变量或密钥配置。
