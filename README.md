# Enterprise Insight Agent｜企业知识检索与经营分析智能体

一个面向企业公开资料的、可解释的 RAG 学习项目。当前版本先完成最小可运行闭环：读取 PDF、切分文本、关键词检索、把相关原文交给 DeepSeek，并返回可追溯引用。

> 项目策略：先建立能运行、能测试、能解释的 baseline，再逐步升级 Embedding、BM25、Hybrid Retrieval、Reranker 和经营分析 Agent。

## 当前能力（v0.1）

- 读取一个或多个文本型 PDF，并保留文件名和页码；
- 按页进行带重叠的字符切块，生成唯一 `chunk_id`；
- 使用轻量 TF-IDF + 查询词覆盖率进行中英文关键词检索；
- 通过 OpenAI-compatible SDK 调用 DeepSeek；
- 要求回答仅依据检索上下文，并使用 `[1]`、`[2]` 标注依据；
- CLI 支持单次提问与连续交互，也可打印召回原文；
- 内置零下载示例 PDF 生成脚本和单元测试。

当前限制：不支持扫描件 OCR、表格结构恢复和语义同义词检索。这些限制是后续迭代的明确起点。

## 架构

```mermaid
flowchart LR
    A["企业 PDF"] --> B["逐页提取文本"]
    B --> C["Chunk + 来源元数据"]
    C --> D["关键词检索 baseline"]
    D --> E["Top-K Context"]
    E --> F["DeepSeek 生成"]
    F --> G["答案 + 引用来源"]
```

| 模块 | 文件 | 职责 |
|---|---|---|
| Ingestion | `app/ingestion.py` | PDF 读取、文本清洗、页码保留 |
| Chunking | `app/chunking.py` | 页内切块、重叠窗口、chunk id |
| Retrieval | `app/retrieval.py` | 中英文分词与可解释的关键词排序 |
| LLM | `app/llm.py` | Context 拼装、DeepSeek 调用、回答约束 |
| Pipeline | `app/pipeline.py` | 串联各模块，支持一次加载、多次提问 |
| CLI | `main.py` | 参数解析、交互提问、引用展示 |

## Windows 安装

项目已在 Python 3.13 设计环境下开发。PowerShell 中执行：

```powershell
git clone https://github.com/Mistriptide/enterprise-insight-agent.git
cd enterprise-insight-agent

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

如果 PowerShell 阻止激活脚本，可仅对当前终端执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 配置 DeepSeek

复制示例配置：

```powershell
Copy-Item .env.example .env
```

然后只在本地 `.env` 中填写：

```dotenv
DEEPSEEK_API_KEY=你的真实Key
DEEPSEEK_MODEL=deepseek-flash
```

`.env` 已被 `.gitignore` 排除。不要把真实 Key 写进代码、README、截图或提交记录。

## 5 分钟示例流程

1. 生成一个包含两页经营信息的示例 PDF：

```powershell
python scripts/create_sample_pdf.py
```

2. 运行一次完整问答：

```powershell
python main.py --pdf data/sample_company_report.pdf --question "What are the main operating risks?" --show-context
```

3. 或进入连续提问模式：

```powershell
python main.py --pdf data/sample_company_report.pdf --show-context
```

示例问题：

- `What was the 2025 revenue?`
- `What are the main operating risks?`
- `What is the company's 2026 priority?`

CLI 会显示模型回答，以及类似下面的可追溯来源：

```text
[1] sample_company_report.pdf · 第 2 页 · sample_company_report-p2-c1
```

使用自己的资料时，可以重复传入 `--pdf`：

```powershell
python main.py --pdf data/annual_report.pdf --pdf data/esg_report.pdf -q "公司的主要增长来源是什么？"
```

注意：当前版本只支持含文本层的 PDF。若 PDF 是扫描图片，程序会提示需要 OCR。

## 测试

```powershell
python -m pytest
```

测试不调用 DeepSeek、不会消耗 API 额度，覆盖：示例 PDF 提取、页码元数据、Chunk 重叠、参数校验、中英文关键词检索和 Context 引用格式。

## RAG 闭环如何工作

1. `pypdf` 逐页提取文字，文件名与一基页码进入元数据。
2. 每页独立切成约 700 字符的 Chunk，相邻块重叠 100 字符，减少边界信息损失。
3. 检索器把英文拆成单词，把连续中文拆成单字和双字词，计算 TF-IDF 分数并加入查询覆盖率。
4. 只把得分最高的 Top-K Chunk 送给 DeepSeek，而不是发送整份 PDF。
5. Prompt 要求模型只依据 Context 作答；CLI 同时打印真实检索来源，方便核验。

## 项目结构

```text
enterprise-insight-agent/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── ingestion.py
│   ├── chunking.py
│   ├── retrieval.py
│   ├── llm.py
│   └── pipeline.py
├── data/
│   └── .gitkeep
├── scripts/
│   └── create_sample_pdf.py
├── tests/
│   ├── test_chunking.py
│   ├── test_ingestion.py
│   ├── test_llm.py
│   └── test_retrieval.py
├── .env.example
├── .gitignore
├── main.py
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## 迭代路线

- **v0.1（当前）**：最小 RAG 闭环 + 关键词 baseline + 引用 + CLI + 测试；
- **v0.2**：Embedding 与本地向量索引，并与 baseline 做同题对比；
- **v0.3**：BM25 + Vector Hybrid Retrieval，加入可复现评测集；
- **v0.4**：Reranker 与检索/生成指标；
- **v0.5**：企业经营分析 Agent、结构化报告和 Streamlit Demo。

## 面试时可以怎么介绍

“我没有一开始堆叠 LangChain 等框架，而是先实现了一个可解释的 RAG baseline。系统逐页解析企业 PDF，保留文件名、页码和 chunk id，用轻量词法检索召回证据，再通过 OpenAI-compatible 接口调用 DeepSeek，并将引用与答案一起展示。这样后续加入向量检索、混合检索和 Reranker 时，可以用同一批问题与 baseline 比较，而不是只说组件更多。”

## 安全说明

- 仓库只包含 `.env.example`，不包含真实密钥；
- 模型只接收被召回的文本块，生产环境仍需增加敏感信息识别、权限控制和审计；
- 生成答案可能出错，关键经营结论必须回到引用原文核验。
