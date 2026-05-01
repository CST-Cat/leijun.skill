# 雷军思维蒸馏项目

## 目标
从雷军近 40 年公开信息中蒸馏出能模拟雷军思维方式的 Skill。

## 项目结构

```
leijun/
├── leijun.skill/              ← 项目一：纯 SKILL.md（给别人用）
│   ├── SKILL.md               核心产物，可直接安装
│   ├── references/research/   6个调研文件
│   └── examples/              效果演示
│
├── leijun.skill-rag/          ← 项目二：SKILL.md + 向量检索（你自己用）
│   ├── SKILL.md               与项目一相同 + 检索指令
│   ├── mcp/                   MCP Server
│   ├── scripts/               入库/检索脚本
│   └── references/research/   与项目一共享
│
└── data/raw/                  ← 原始数据（leijun.skill-rag 入库用）
    ├── books/        8本书
    ├── interviews/   22篇访谈
    ├── speeches/     16篇演讲
    └── wechat/       16篇微信文章
```

## 使用方式

- `/leijun`：纯人设回答（不依赖 MCP）
- `/leijun-rag`：人设 + 自动检索原始材料（需要 leijun-rag MCP）
