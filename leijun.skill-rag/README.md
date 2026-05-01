# 雷军.skill-rag

**雷军的认知操作系统 + 向量检索版。**

在 [leijun.skill](../leijun.skill/) 的基础上，增加向量检索能力，支持更丰富的数据和更精准的事实引用。

## 与 leijun.skill 的区别

| | leijun.skill | leijun.skill-rag |
|---|---|---|
| SKILL.md | 相同 | 相同 + 检索指令 |
| 知识来源 | 精炼在 SKILL.md 中 | SKILL.md + 向量库原始材料 |
| 事实引用 | 模型推理 | 可检索原始原文 |
| 数据量 | 受 SKILL.md 长度限制 | 几乎无限 |
| 依赖 | 无 | Python + ChromaDB + Embedding API |
| 适合场景 | 分享给别人 | 个人深度使用 |

## 快速开始

### 1. 安装依赖

```bash
cd leijun.skill-rag/scripts
pip install -r requirements.txt
```

### 2. 数据入库

```bash
python ingest.py
```

默认读取 `data/raw/` 目录下的 md 文件入库。

入库完成后，向量库在 `leijun.skill-rag/data/` 目录。

### 3. 命令行测试

```bash
python search.py "雷军为什么造车"
python search.py "极致性价比" -t book -n 3
python search.py "顺势而为" -y 2024
```

### 4. 配置 MCP Server

在 Claude Code 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "leijun-rag": {
      "command": "python",
      "args": ["/path/to/leijun.skill-rag/mcp/vector_rag_mcp.py"],
      "env": {
        "EMBEDDING_API_URL": "https://router.tumuer.me/v1/embeddings",
        "EMBEDDING_API_KEY": "your-key-here",
        "EMBEDDING_MODEL": "Qwen3-VL-Embedding-8B",
        "CHROMA_DB_PATH": "/path/to/leijun.skill-rag/data"
      }
    }
  }
}
```

### 5. 安装 SKILL.md

将 `SKILL.md` 复制到 `~/.claude/skills/leijun/SKILL.md`。

## 架构

```
用户提问
  │
  ▼
┌─────────────────────────────────────────────┐
│  Claude Code (主进程)                         │
│                                              │
│  1. 读取 SKILL.md → 加载人设/价值观/风格       │
│  2. 判断是否需要检索向量库                      │
│  3. 如需要 → 调用 MCP 工具 search_documents    │
│  4. 拿到检索结果 → 结合人设生成回答             │
└──────────────┬──────────────────────────────┘
               │ MCP 协议 (stdio)
               ▼
┌─────────────────────────────────────────────┐
│  vector_rag_mcp.py (MCP Server)             │
│                                              │
│  search_documents(query, filter_metadata):   │
│    ① query → Embedding API → 向量 [1024维]    │
│    ② 向量 → ChromaDB cosine 检索 → Top-K 文档  │
│    ③ 返回文档内容 + 元数据                     │
└──────────────┬──────────────────────────────┘
               │ HTTP
               ▼
┌─────────────────────────────────────────────┐
│  Embedding API (远程)                         │
│  Qwen3-VL-Embedding-8B                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  ChromaDB (本地磁盘)                          │
│  HNSW 索引 + cosine 距离                     │
└─────────────────────────────────────────────┘
```

## 仓库结构

```
leijun.skill-rag/
├── SKILL.md                    ← 与 leijun.skill 相同 + 检索指令
├── README.md
├── scripts/
│   ├── ingest.py               ← 数据入库脚本
│   ├── search.py               ← 命令行检索工具
│   └── requirements.txt
├── mcp/
│   └── vector_rag_mcp.py       ← MCP Server
├── data/
│   └── .gitkeep                ← ChromaDB 数据（不提交）
├── references/                 ← 调研文件（与 leijun.skill 共享）
├── .gitignore
└── LICENSE
```

## Embedding 模型

默认使用 `Qwen3-VL-Embedding-8B`，可通过环境变量切换：

```bash
export EMBEDDING_API_URL="https://your-api-url/v1/embeddings"
export EMBEDDING_API_KEY="your-key"
export EMBEDDING_MODEL="your-model"
```

## 许可证

MIT
