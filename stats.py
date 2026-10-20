"""让数据库替你算 —— 分组统计

以前在记账程序里，你想知道"每种类型各有多少笔"，得这么写：

    counts = {}
    for item in records:
        t = item["type"]
        counts[t] = counts[t] + 1

现在，一句 SQL。
"""
import sqlite3

conn = sqlite3.connect("ledger.db")
cur = conn.cursor()

# 按"状态"分组，数一数每种状态各有多少台设备
cur.execute("""
    SELECT status, COUNT(*)
    FROM devices
    GROUP BY status
""")


for row in cur.fetchall():
    print(row)

conn.close()
