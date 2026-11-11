"""一次问 3 个问题，看这套 RAG 在哪些问题上会翻车

三个问题分别考三种能力：
  ① 口语 → 书面语（能不能对上）
  ② 手册里根本没有的东西（会不会老实说没有）
  ③ 精确的故障码查询（能不能查准）
"""

import rag_vec as R

QUESTIONS = [
    "UPS 老跳闸怎么办",
    "泡水了还能用吗",
    "E07 什么意思",
]

if __name__ == "__main__":
    R.build()

    for q in QUESTIONS:
        R.ask(q)
        print("=" * 60)
