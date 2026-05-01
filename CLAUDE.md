# 雷军思维蒸馏项目

## 目标
从雷军近 40 年公开信息中蒸馏出能模拟雷军思维方式的 Skill。

## 项目结构

```
leijun/
├── leijun.skill/              ← 纯 SKILL.md（零依赖，开箱即用）
│   ├── SKILL.md               核心产物，可直接安装
│   ├── references/research/   6个调研文件
│   └── examples/              效果演示
│
├── leijun.skill-rag/          ← SKILL.md + 向量检索（支持原文引用）
│   ├── SKILL.md               与项目一相同 + 检索指令
│   ├── mcp/                   MCP Server
│   ├── scripts/               入库/检索脚本
│   ├── references/research/   与项目一共享
│   └── data/raw/              62个原始数据文件（入库用）
│       ├── books/       8本书
│       ├── interviews/   22篇访谈
│       ├── speeches/     16篇演讲
│       └── wechat/       16篇微信文章
│
└── LICENSE                    MIT 许可证
```

## 使用方式

- `/leijun`：纯人设回答（不依赖 MCP）
- `/leijun-rag`：人设 + 自动检索原始材料（需要 leijun-rag MCP）

## 注意事项

- `data/raw/` 中的原始材料仅供学习研究，版权归原作者所有
- SKILL.md 中的金句均为原文引用，标注来源
