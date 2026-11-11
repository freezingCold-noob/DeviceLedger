"""最小 RAG —— 不引框架、不装模型

流程：切块 → 建库 → 选章节 → 检索 → 组装 prompt → 问 DeepSeek

⚠️ 检索仍然是笨办法（比字）。但加了一招：
   先把手册目录给模型看，让它选"翻哪一节"，再只在那一节里比字。
   相当于人查手册：先看目录，再翻到那一页。
"""

import os
import re
import sqlite3

import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("DEEPSEEK_API_KEY")
DB = "rag.db"
TOP_K = 3
TITLE = re.compile(r"^\d+\.\d+\s")      # 形如 "3.1 频繁断电重启的处置"


# ══════════════════════════════════════════════════
#  ① 切块：按空行分段，顺手记住"这一段属于哪一节"
# ══════════════════════════════════════════════════
def cut(path="manual.txt", max_len=300):
    text = open(path, encoding="utf-8").read()
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    section = "开头"
    for p in paras:
        if TITLE.match(p):
            section = p                    # 遇到标题行，就换一节
        if len(p) <= max_len:
            chunks.append((section, p))
        else:
            for i in range(0, len(p), max_len):
                chunks.append((section, p[i:i + max_len]))
    return chunks


# ══════════════════════════════════════════════════
#  ② 建库
# ══════════════════════════════════════════════════
def build():
    chunks = cut()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS chunks")
    cur.execute("""
        CREATE TABLE chunks (
            id      INTEGER PRIMARY KEY,
            section TEXT,
            text    TEXT
        )
    """)
    for sec, c in chunks:
        cur.execute("INSERT INTO chunks (section, text) VALUES (?, ?)", (sec, c))
    conn.commit()

    n = cur.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    secs = cur.execute("SELECT DISTINCT section FROM chunks").fetchall()
    conn.close()

    print(f"✅ 建库完成：{n} 个片段，{len(secs)} 节")
    return n


# ══════════════════════════════════════════════════
#  ③ 先选章节：把目录给模型看
#     这一步能成，是因为"标题是人写的、说人话的"
# ══════════════════════════════════════════════════
def pick_section(question):
    conn = sqlite3.connect(DB)
    sections = [r[0] for r in conn.execute(
        "SELECT DISTINCT section FROM chunks").fetchall()]
    conn.close()

    lst = "\n".join(f"- {s}" for s in sections)

    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": (
                    "下面是设备手册的目录。用户问了一个问题，请判断该翻哪一节。\n"
                    "只输出那一节的标题原文，一个字都不要改，不要解释。\n\n"
                    f"目录：\n{lst}\n\n"
                    f"用户的问题：{question}"
                ),
            }],
        },
        timeout=60,
    )
    return r.json()["choices"][0]["message"]["content"].strip().splitlines()[0]


# ══════════════════════════════════════════════════
#  ④ 把选中的那一节整节取出来
#     章节已经帮你把范围从 24 段缩到 2 段，不必再算分
# ══════════════════════════════════════════════════
def fetch_section(section, k=TOP_K):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, text FROM chunks WHERE section LIKE ? ORDER BY id",
        (f"%{section[:6]}%",),
    ).fetchall()
    conn.close()
    return rows[:k]


# ══════════════════════════════════════════════════
#  ⑤ 组装 prompt → 问模型
# ══════════════════════════════════════════════════
def ask(question):
    sec = pick_section(question)
    print(f"\n你的问题：{question}")
    print(f"翻开这一节：{sec}")

    hits = fetch_section(sec)
    print("─" * 50)
    print(f"这一节共 {len(hits)} 段，全给模型：")
    for i, (cid, text) in enumerate(hits, 1):
        print(f"  [{i}] 片段 {cid}｜{text[:30]}…")

    ctx = "\n\n".join(f"[片段{cid}]\n{text}" for cid, text in hits)

    prompt = f"""只根据下面给出的资料回答。资料里没有的内容，直接回答"手册里没写"，不要凭常识补充。
注意：用户说的是口语，资料里是书面语，两者可能用词不同（例如"跳闸"就是"断电重启"），请对应理解。

资料：
{ctx}

问题：{question}"""

    print("─" * 50)
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {KEY}"},
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
