# VLM Paper Agent

中文说明见下方，English version follows.

## 中文版

### 后续更新计划
#### 1.加入爬取方案
#### 2.加入作者title的获取
#### 3.输出精确引用序号，并优化输出格式

### 项目简介

VLM Paper Agent 是一个面向学术调研的命令行工具，聚焦两个高频需求：

- 按作者姓名检索 Google Scholar 论文列表
- 按论文标题检索被引论文，并抽取引用上下文

项目使用兼容 OpenAI API 的大模型作为编排与整理层，使用 Google Scholar / Semantic Scholar 作为数据来源，最终输出适合阅读和保存的 Markdown 风格研究结果。默认配置使用 DashScope 上的 Qwen，但也可以切换到其他兼容平台。

### 当前开源范围

当前版本仅开源 3 个核心文件：

- `main.py`：命令行入口，负责加载环境变量、接收用户输入、保存输出
- `agent.py`：Agent 编排层，负责工具调用、批处理和结果整理，并支持自定义 `base_url` 和 `model`
- `tools/scholar_tools.py`：数据抓取层，负责调用 Google Scholar 和 Semantic Scholar

实验脚本、临时数据文件、研究过程材料暂不包含在开源范围内。

### 功能特性

- 作者检索：根据作者姓名获取 Google Scholar 档案中的论文列表
- 引文分析：根据论文标题获取 citing papers、作者、引用上下文等信息
- 批量整理：对引文结果分批并行处理，生成结构化中文报告
- 本地保存：每次查询都会单独生成一个结果文件，保存在 `outputs/` 目录下

### 工作流程

1. 用户在命令行输入问题
2. `agent.py` 使用 Qwen 判断应调用哪个工具
3. `tools/scholar_tools.py` 获取外部学术数据
4. 若是引文分析任务，Agent 会并行分批整理结果
5. 最终输出到终端，并保存到本地独立结果文件

### 项目结构

```text
.
├─ main.py
├─ agent.py
├─ tools/
│  └─ scholar_tools.py
└─ requirements.txt
```

### 环境要求

- Python 3.10+
- 一个兼容 OpenAI API 的模型服务 Key
- 可选：Semantic Scholar API Key

### 安装

```bash
pip install -r requirements.txt
```

### 环境变量

在项目根目录创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen3.5-plus
S2_API_KEY=your_semantic_scholar_api_key
```

说明：

- `OPENAI_API_KEY`：必填，任意兼容 OpenAI API 的平台均可使用
- `OPENAI_BASE_URL`：选填，默认值为 DashScope 的兼容接口地址
- `OPENAI_MODEL`：选填，默认值为 `qwen3.5-plus`
- `S2_API_KEY`：选填，用于提高 Semantic Scholar API 的稳定性和额度
- 为兼容旧配置，代码仍支持 `DASHSCOPE_API_KEY`

如果你想切换到其他平台，只需替换 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`，并填入对应平台的 API Key。

输出文件会按 `时间戳_查询摘要.txt` 的格式保存，例如：

```text
outputs/20260313_153045_Attention_is_all_you_need.txt
```

### 运行方式

```bash
python main.py
```

### 示例输入

```text
请帮我找一下论文 'Attention is all you need' 的引用文，列出作者和引用时的句子。
```

```text
帮我搜索 'Ilya Sutskever' 的所有论文。
```

### 数据来源

- Google Scholar：作者检索
- Semantic Scholar Graph API：论文引用与引用上下文
- 任意 OpenAI-Compatible API：模型推理与结果整理

### 已知限制

- `scholarly` 依赖 Google Scholar，稳定性受网络和频率限制影响
- Semantic Scholar 并非每篇 citing paper 都提供完整 `contexts`（后续加入爬取的方式），尤其是部分需求登录的期刊论文
- 当前版本主要面向命令行使用，尚未提供 Web UI 或标准化 API 服务
- 不同平台对 OpenAI 兼容接口的细节支持程度不同，个别平台可能需要额外适配
- AI存在幻觉，引用上下文可能存在错误，请仔细核对

### 适用场景

- 论文调研与 related work 快速梳理
- 查找某篇经典论文如何被后续工作引用
- 按作者快速拉取论文列表
- 为人工文献综述提供初步材料

---

## English

### Overview

VLM Paper Agent is a command-line research assistant for academic literature exploration. It focuses on two common workflows:

- Search an author's paper list from Google Scholar
- Search citing papers for a given paper title and extract citation contexts

The project uses an OpenAI-compatible LLM for orchestration and formatting, while Google Scholar and Semantic Scholar provide the research data. The default setup uses Qwen via DashScope, but the client can also be pointed to other compatible providers.

### Open-Source Scope

This open-source version currently includes only 3 core files:

- `main.py`: CLI entry point, environment loading, input loop, output persistence
- `agent.py`: agent orchestration, tool calling, batching, report assembly, and configurable `base_url` / `model`
- `tools/scholar_tools.py`: data access layer for Google Scholar and Semantic Scholar

Experimental scripts, temporary datasets, and private research artifacts are intentionally excluded from this release.

### Features

- Author lookup from Google Scholar
- Citation analysis for a paper title
- Extraction of citing paper metadata, citation intents, and citation contexts
- Parallel batch formatting for large citation results
- Automatic saving of each query result as a separate file under `outputs/`

### How It Works

1. The user enters a query in the terminal
2. `agent.py` uses Qwen to decide which tool to call
3. `tools/scholar_tools.py` fetches academic data from external sources
4. For citation-analysis tasks, results are processed in parallel batches
5. The final report is printed to the terminal and saved as a separate local file

### Project Structure

```text
.
├─ main.py
├─ agent.py
├─ tools/
│  └─ scholar_tools.py
└─ requirements.txt
```

### Requirements

- Python 3.10+
- An OpenAI-compatible API key
- Optional: Semantic Scholar API key

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen3.5-plus
S2_API_KEY=your_semantic_scholar_api_key
```

Notes:

- `OPENAI_API_KEY`: required, works with any OpenAI-compatible provider
- `OPENAI_BASE_URL`: optional, defaults to the DashScope compatible endpoint
- `OPENAI_MODEL`: optional, defaults to `qwen3.5-plus`
- `S2_API_KEY`: optional, but recommended for more stable Semantic Scholar access
- For backward compatibility, `DASHSCOPE_API_KEY` is still supported

To use another provider, replace `OPENAI_BASE_URL` and `OPENAI_MODEL` with the target platform's values.

Output files are saved using the pattern `timestamp_query-summary.txt`, for example:

```text
outputs/20260313_153045_Attention_is_all_you_need.txt
```

### Run

```bash
python main.py
```

### Example Queries

```text
Please find papers citing 'Attention is all you need', and list the authors and citation sentences.
```

```text
Find all papers by 'Ilya Sutskever'.
```

### Data Sources

- Google Scholar for author lookup
- Semantic Scholar Graph API for citations and citation contexts
- Any OpenAI-compatible API for model-based orchestration and formatting

### Known Limitations

- The `scholarly` package depends on Google Scholar behavior and may be rate-limited or unstable
- Semantic Scholar does not always return complete citation contexts for every citing paper
- The current ranking logic uses the last author's h-index as one heuristic feature; this is an engineering approximation
- The current release is CLI-first and does not provide a web interface or production API
- OpenAI-compatible behavior varies across providers, so some platforms may need minor adaptation

### Use Cases

- Literature review preparation
- Related-work exploration
- Understanding how influential papers are cited in later work
- Quickly collecting an author's publication list
