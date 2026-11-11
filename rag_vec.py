"""向量版 RAG —— 不看目录，直接比意思

和 rag_min.py 的区别只有一处：
  rag_min.py：问句 → 让模型看目录选一节 → 只在这一节里比字
  rag_vec.py：问句 → 变成 1024 个数字 → 和所有片段算相似度 → 取前 3

这样同一句话"UPS 老跳闸怎么办"，两个版本的结果可以直接对比。
"""

import json
import math
import os
import re
import sqlite3

import requests
from dotenv import load_dotenv

load_dotenv()

DS_KEY = os.getenv("DEEPSEEK_API_KEY")          # 用来回答
SF_KEY = os.getenv("SILICONFLOW_API_KEY")       # 用来算向量
DB = "rag_vec.db"
TOP_K = 3
EMB_MODEL = "BAAI/bge-m3"
TITLE = re.compile(r"^\d+\.\d+\s")


# ══════════════════════════════════════════════════
#  ① 切块（和上一版完全一样，只是不再需要章节）
# ══════════════════════════════════════════════════
def cut(path="manual.txt", max_len=300):
    text = open(path, encoding="utf-8").read()
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    section = "开头"
    for p in paras:
        if TITLE.match(p):
            section = p
        if len(p) <= max_len:
            chunks.append((section, p))
        else:
            for i in range(0, len(p), max_len):
                chunks.append((section, p[i:i + max_len]))
    return chunks


# ══════════════════════════════════════════════════
#  ② 把文字变成向量（调用硅基流动的 bge-m3）
#     一次可以传多条，省调用次数
# ══════════════════════════════════════════════════
def embed(texts):
    r = requests.post(
        "https://api.siliconflow.cn/v1/embeddings",
        headers={"Authorization": f"Bearer {SF_KEY}"},
        json={"model": EMB_MODEL, "input": texts},
        timeout=90,
    )
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]


# ══════════════════════════════════════════════════
#  ③ 建库：每段算一次向量，存进数据库
# ══════════════════════════════════════════════════
def build():
    chunks = cut()
    print(f"切成 {len(chunks)} 段，正在算向量（1 次调用）…")

    vecs = embed([c for _, c in chunks])

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS chunks")
    cur.execute("""
        CREATE TABLE chunks (
            id   INTEGER PRIMARY KEY,
            sec  TEXT,
            text TEXT,
            vec  TEXT
        )
    """)
    for (sec, text), v in zip(chunks, vecs):
        cur.execute(
            "INSERT INTO chunks (sec, text, vec) VALUES (?, ?, ?)",
            (sec, text, json.dumps(v)),
        )
    conn.commit()
    conn.close()

    print(f"✅ 建库完成：{len(chunks)} 段，每段 {len(vecs[0])} 个数字")


# ══════════════════════════════════════════════════
#  ④ 算相似度：两个向量的方向有多接近
# ══════════════════════════════════════════════════
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb)


def search(question, k=TOP_K):
    qv = embed([question])[0]           # 问答时只有这 1 次调用

    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT id, sec, text, vec FROM chunks").fetchall()
    conn.close()

    scored = [(cosine(qv, json.loads(v)), cid, sec, text)
              for cid, sec, text, v in rows]
    scored.sort(reverse=True)
    return scored[:k]


# ══════════════════════════════════════════════════
#  ⑤ 组装 prompt → 问模型（和上一版一样）
# ══════════════════════════════════════════════════
def ask(question):
    hits = search(question)

    print(f"\n你的问题：{question}")
    print("─" * 50)
    print(f"按『意思像不像』排前 {len(hits)} 段：")
    for i, (score, cid, sec, text) in enumerate(hits, 1):
        print(f"  [{i}] 相似度 {score:.3f}｜片段 {cid}｜{text[:30]}…")

    ctx = "\n\n".join(f"[片段{cid}]\n{text}" for _, cid, _, text in hits)

    prompt = f"""只根据下面给出的资料回答。资料里没有的内容，直接回答"手册里没写"，不要凭常识补充。
注意：用户说的是口语，资料里是书面语，两者可能用词不同（例如"跳闸"就是"断电重启"），请对应理解。

资料：
{ctx}

问题：{question}"""

    print("─" * 50)
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {DS_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    print("HTTP", r.status_code)
    print("\n模型回答：")
    print(r.json()["choices"][0]["message"]["content"])


if __name__ == "__main__":
    build()
    ask("UPS 老跳闸怎么办")
