#!/usr/bin/env python3
"""
雷军思维蒸馏 - 向量检索 MCP Server
基于 Qwen3-VL-Embedding-8B + ChromaDB
"""

import os
import json
import hashlib
from typing import List, Optional

import chromadb
import requests
from mcp.server.fastmcp import FastMCP

# ============ 配置 ============
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://router.tumuer.me/v1/embeddings")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen3-VL-Embedding-8B")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data"))
COLLECTION_NAME = "leijun_docs"

# ============ 初始化 ============
mcp = FastMCP("leijun-rag")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection():
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def call_embedding_api(texts: List[str]) -> List[List[float]]:
    headers = {"Content-Type": "application/json"}
    if EMBEDDING_API_KEY:
        headers["Authorization"] = f"Bearer {EMBEDDING_API_KEY}"
    resp = requests.post(
        EMBEDDING_API_URL,
        headers=headers,
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=30,
    )
    if resp.status_code != 200:
        raise Exception(f"API Error {resp.status_code}: {resp.text[:200]}")
    return [item["embedding"] for item in resp.json()["data"]]


def doc_id(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()


# ============ MCP 工具 ============


@mcp.tool()
def add_document(content: str, metadata: Optional[str] = None) -> str:
    """添加文档到向量库"""
    col = get_collection()
    meta = json.loads(metadata) if metadata else {}
    meta["content_preview"] = content[:100]
    did = doc_id(content)
    col.add(
        ids=[did],
        embeddings=call_embedding_api([content]),
        documents=[content],
        metadatas=[meta],
    )
    return f"已添加，ID: {did[:8]}..."


@mcp.tool()
def batch_add_documents(documents: str) -> str:
    """批量添加文档，JSON 数组格式"""
    col = get_collection()
    docs = json.loads(documents)
    if not docs:
        return "没有文档"
    contents = [d["content"] for d in docs]
    ids = [doc_id(c) for c in contents]
    all_emb = []
    for i in range(0, len(contents), 100):
        all_emb.extend(call_embedding_api(contents[i : i + 100]))
    metas = [
        {**d.get("metadata", {}), "content_preview": d["content"][:100]} for d in docs
    ]
    col.add(ids=ids, embeddings=all_emb, documents=contents, metadatas=metas)
    return f"成功添加 {len(docs)} 个文档"


@mcp.tool()
def search_documents(
    query: str,
    n_results: int = 5,
    filter_metadata: Optional[str] = None,
) -> str:
    """语义搜索文档。支持元数据过滤，如 {"type": "speech"} 或 {"year": {"$gte": 2020}}"""
    col = get_collection()
    q_emb = call_embedding_api([query])[0]
    where = json.loads(filter_metadata) if filter_metadata else None
    results = col.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    if results["documents"] and results["documents"][0]:
        for i, (d, m, dist) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            meta = {k: v for k, v in m.items() if k != "content_preview"}
            line = f"结果{i+1} (相似度:{1-dist:.2%}): {d[:500]}"
            if meta:
                line += f" | {json.dumps(meta, ensure_ascii=False)}"
            output.append(line)
    return "\n".join(output) if output else "未找到相关文档"


@mcp.tool()
def list_documents(limit: int = 20) -> str:
    """列出向量库中的文档"""
    col = get_collection()
    count = col.count()
    if count == 0:
        return "向量库为空"
    results = col.get(limit=limit, include=["documents", "metadatas"])
    output = [f"共 {count} 个文档:"]
    for i, (did, d, m) in enumerate(
        zip(results["ids"], results["documents"], results["metadatas"])
    ):
        meta = {k: v for k, v in m.items() if k != "content_preview"} if m else {}
        line = f"{i+1}. [{did[:8]}] {d[:80]}"
        if meta:
            line += f" | {json.dumps(meta, ensure_ascii=False)}"
        output.append(line)
    return "\n".join(output)


@mcp.tool()
def delete_document(doc_id: str) -> str:
    """删除文档（支持前缀匹配）"""
    col = get_collection()
    if len(doc_id) < 32:
        matches = [i for i in col.get(include=[])["ids"] if i.startswith(doc_id)]
        if not matches:
            return f"未找到 ID 以 {doc_id} 开头的文档"
        if len(matches) > 1:
            return "匹配到多个，请提供更长前缀"
        doc_id = matches[0]
    col.delete(ids=[doc_id])
    return "已删除"


@mcp.tool()
def clear_documents() -> str:
    """清空向量库"""
    chroma_client.delete_collection(COLLECTION_NAME)
    get_collection()
    return "已清空"


@mcp.tool()
def get_collection_stats() -> str:
    """获取向量库统计信息"""
    col = get_collection()
    count = col.count()
    # 按类型统计
    type_stats = {}
    if count > 0:
        results = col.get(include=["metadatas"])
        for m in results["metadatas"]:
            if m:
                t = m.get("type", "unknown")
                type_stats[t] = type_stats.get(t, 0) + 1
    stats = f"集合:{COLLECTION_NAME} | 文档数:{count} | 路径:{CHROMA_DB_PATH} | 模型:{EMBEDDING_MODEL}"
    if type_stats:
        stats += f"\n按类型: {json.dumps(type_stats, ensure_ascii=False)}"
    return stats


# ============ 运行 ============
if __name__ == "__main__":
    mcp.run(transport="stdio")
