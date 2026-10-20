"""设备台账 —— 第一次用数据库

和记账程序的区别：
    以前：数据存在 records.json 里，想算总数得自己写循环一条条加
    现在：数据住在数据库里，想算什么，让数据库自己算
"""
import sqlite3

# 打开数据库。
# 文件不存在就自动新建一个，所以第一次跑也不会报错。
conn = sqlite3.connect("ledger.db")

# 从连接上拿一个"操作员"，后面所有 SQL 都通过它来执行
cur = conn.cursor()

# ── ① 建一张表 ────────────────────────────────────────
# 表名：devices（设备）
# 四个列：id / name / location / status
cur.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id       INTEGER PRIMARY KEY,
        name     TEXT,
        location TEXT,
        status   TEXT
    )
""")

# ── ② 插一台设备进去 ──────────────────────────────────
cur.execute(
    "INSERT INTO devices (name, location, status) VALUES (?, ?, ?)",
    ("空压机 1 号", "一号车间", "运行中"),
)

cur.execute(
    "UPDATE devices SET status = ? WHERE id = ?",
    ("维修中", 1)
)
# ── ③ 填空 A ──────────────────────────────────────────
# 光是 execute 还不算数，得让改动"落实"下来。
# 这个方法叫什么？（git 里也有一个同名的东西，意思也是"落实"）
conn.commit()

# ── ④ 填空 B ──────────────────────────────────────────
# 把 devices 表里所有的行查出来。SQL 里"查"这个动词是哪个？
# （想不起来就告诉我，我把它改成二选一）
cur.execute("SELECT * FROM devices")

# 把查询结果取到手上
rows = cur.fetchall()


for r in rows:
    print(r)

# 关门
conn.close()
