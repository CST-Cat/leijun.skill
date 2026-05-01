#!/usr/bin/env python3
"""
数据入库脚本
将雷军的原始材料（md文件）批量导入向量库
"""

import os
import re
import json
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
import requests

# ============ 配置 ============
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://router.tumuer.me/v1/embeddings")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen3-VL-Embedding-8B")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data"))
COLLECTION_NAME = "leijun_docs"

# ============ 工具函数 ============


def call_embedding_api(texts: List[str]) -> List[List[float]]:
    """调用 Embedding API"""
    headers = {"Content-Type": "application/json"}
    if EMBEDDING_API_KEY:
        headers["Authorization"] = f"Bearer {EMBEDDING_API_KEY}"
    resp = requests.post(
        EMBEDDING_API_URL,
        headers=headers,
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=60,
    )
    if resp.status_code != 200:
        raise Exception(f"API Error {resp.status_code}: {resp.text[:200]}")
    return [item["embedding"] for item in resp.json()["data"]]


def doc_id(content: str) -> str:
    """生成文档ID"""
    return hashlib.md5(content.encode()).hexdigest()


def parse_frontmatter(content: str) -> tuple:
    """解析 YAML frontmatter"""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return {}, content
    frontmatter_str = match.group(1)
    body = match.group(2)
    meta = {}
    for line in frontmatter_str.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body


def chunk_text(text: str, max_chars: int = 2000) -> List[str]:
    """按段落切片，每片不超过 max_chars 字符"""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks if chunks else [text[:max_chars]]


def infer_type_from_path(file_path: str) -> str:
    """从文件路径推断类型"""
    path_lower = file_path.lower()
    if "book" in path_lower or "书" in path_lower:
        return "book"
    elif "interview" in path_lower or "访谈" in path_lower:
        return "interview"
    elif "speech" in path_lower or "演讲" in path_lower:
        return "speech"
    elif "wechat" in path_lower or "微信" in path_lower:
        return "wechat"
    else:
        return "article"


def infer_year_from_filename(filename: str) -> Optional[int]:
    """从文件名推断年份"""
    match = re.search(r"(20\d{2}|19\d{2})", filename)
    if match:
        return int(match.group(1))
    return None


# ============ 主逻辑 ============


def process_file(file_path: str, data_root: str) -> List[Dict]:
    """处理单个文件，返回文档列表"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter, body = parse_frontmatter(content)
    rel_path = os.path.relpath(file_path, data_root)

    # 推断元数据
    doc_type = frontmatter.get("type", infer_type_from_path(rel_path))
    year = frontmatter.get("year", infer_year_from_filename(os.path.basename(file_path)))
    title = frontmatter.get("title", os.path.splitext(os.path.basename(file_path))[0])
    source = frontmatter.get("source", "")

    # 切片
    chunks = chunk_text(body)

    documents = []
    for i, chunk in enumerate(chunks):
        # 构建富文本内容
        prefix = f"【{doc_type}】{title}"
        if year:
            prefix += f" ({year}年)"
        prefix += f"\n来源: {rel_path}"
        if i > 0:
            prefix += f" [第{i+1}段]"
        prefix += "\n\n"

        doc_content = prefix + chunk

        metadata = {
            "type": doc_type,
            "title": title,
            "file_path": rel_path,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        if year:
            metadata["year"] = int(year)
        if source:
            metadata["source"] = source

        documents.append({"content": doc_content, "metadata": metadata})

    return documents


def ingest_directory(data_dir: str, collection_name: str = COLLECTION_NAME):
    """入库整个目录"""
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    col = chroma_client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )

    # 获取已有文档ID
    existing_ids = set(col.get(include=[])["ids"])
    print(f"向量库中已有 {len(existing_ids)} 个文档")

    # 扫描文件
    md_files = []
    for root, dirs, files in os.walk(data_dir):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md") and not f.startswith("."):
                md_files.append(os.path.join(root, f))

    print(f"找到 {len(md_files)} 个 md 文件")

    # 处理文件
    all_documents = []
    for file_path in sorted(md_files):
        try:
            docs = process_file(file_path, data_dir)
            all_documents.extend(docs)
        except Exception as e:
            print(f"处理失败 {file_path}: {e}")

    print(f"共生成 {len(all_documents)} 个文档切片")

    # 过滤已存在的
    new_documents = [d for d in all_documents if doc_id(d["content"]) not in existing_ids]
    print(f"新增 {len(new_documents)} 个文档")

    if not new_documents:
        print("没有新文档需要入库")
        return

    # 批量入库
    batch_size = 20
    for i in range(0, len(new_documents), batch_size):
        batch = new_documents[i : i + batch_size]
        contents = [d["content"] for d in batch]
        ids = [doc_id(c) for c in contents]

        print(f"正在入库第 {i+1}-{i+len(batch)} 个文档...")
        embeddings = []
        for j in range(0, len(contents), 10):
            chunk_batch = contents[j : j + 10]
            embeddings.extend(call_embedding_api(chunk_batch))

        metadatas = [
            {**d["metadata"], "content_preview": d["content"][:100]} for d in batch
        ]
        col.add(ids=ids, embeddings=embeddings, documents=contents, metadatas=metadatas)

    print(f"入库完成！向量库中共 {col.count()} 个文档")


# ============ 入口 ============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="雷军思维蒸馏 - 数据入库脚本")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"),
        help="原始数据目录",
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help="ChromaDB 集合名称",
    )
    args = parser.parse_args()

    print(f"数据目录: {args.data_dir}")
    print(f"向量库路径: {CHROMA_DB_PATH}")
    print(f"集合名称: {args.collection}")
    print(f"Embedding 模型: {EMBEDDING_MODEL}")
    print()

    ingest_directory(args.data_dir, args.collection)
