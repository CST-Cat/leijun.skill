#!/usr/bin/env python3
"""
命令行检索工具
用于测试和调试向量检索
"""

import os
import json
import argparse

import chromadb
import requests

# ============ 配置 ============
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://router.tumuer.me/v1/embeddings")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen3-VL-Embedding-8B")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data"))
COLLECTION_NAME = "leijun_docs"


def call_embedding_api(texts):
    headers = {"Content-Type": "application/json"}
    if EMBEDDING_API_KEY:
        headers["Authorization"] = f"Bearer {EMBEDDING_API_KEY}"
    resp = requests.post(
        EMBEDDING_API_URL,
        headers=headers,
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=30,
    )
    return [item["embedding"] for item in resp.json()["data"]]


def search(query: str, n_results: int = 5, filter_type: str = None, filter_year: int = None):
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    col = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    q_emb = call_embedding_api([query])[0]

    where = {}
    if filter_type:
        where["type"] = filter_type
    if filter_year:
        where["year"] = filter_year

    results = col.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        where=where if where else None,
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        print("未找到相关文档")
        return

    for i, (d, m, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        similarity = 1 - dist
        meta = {k: v for k, v in m.items() if k != "content_preview"}
        print(f"\n{'='*60}")
        print(f"结果 {i+1} | 相似度: {similarity:.2%}")
        if meta:
            print(f"元数据: {json.dumps(meta, ensure_ascii=False)}")
        print(f"{'-'*60}")
        print(d[:800])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="雷军思维蒸馏 - 命令行检索")
    parser.add_argument("query", help="搜索查询")
    parser.add_argument("-n", "--n-results", type=int, default=5, help="返回结果数")
    parser.add_argument("-t", "--type", help="按类型过滤 (book/interview/speech/wechat)")
    parser.add_argument("-y", "--year", type=int, help="按年份过滤")
    args = parser.parse_args()

    search(args.query, args.n_results, args.type, args.year)
