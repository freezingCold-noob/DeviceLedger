"""机房设备运维助手 —— 数据层

先建表，再插数据，最后给 API 和 Agent 用。
"""

import sqlite3

conn = sqlite3.connect("ops.db")
cur = conn.cursor()

# ══════════════════════════════════════════════════════════
#  ↓↓↓  这一块你写：建 devices 表，5 列  ↓↓↓
#
#  列名       类型              说明
#  id        INTEGER PRIMARY KEY  编号
#  name      TEXT                 设备名
#  location  TEXT                 位置
#  status    TEXT                 正常 / 故障
#  warranty_end  TEXT             保修到期日 2026-06-30
#
#  照着 devices_db.py 里那段改就行。
# ══════════════════════════════════════════════════════════

cur.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id            INTEGER PRIMARY KEY,
        name          TEXT,
        location      TEXT,
        status        TEXT,
        warranty_end  TEXT
    )
""")

# ══════════════════════════════════════════════════════════
#  ↑↑↑  上面这一块你写  ↑↑↑
# ══════════════════════════════════════════════════════════

# ── 塞 5 台设备进去（机房真实会有的东西）──────────────
# 故意留了两台「故障」、两台「已过保」，这样三个问题才测得出东西
devices = [
    (1, "核心交换机", "3号机架", "正常", "2026-06-30"),   # 已过保
    (2, "接入交换机", "1号机架", "正常", "2028-03-15"),
    (3, "边界防火墙", "机房入口", "故障", "2027-11-20"),
    (4, "UPS 电源",   "2号机架", "故障", "2026-01-10"),   # 已过保
    (5, "汇聚交换机", "2号机架", "正常", "2029-05-01"),
]

for d in devices:
    cur.execute(
        "INSERT OR IGNORE INTO devices (id, name, location, status, warranty_end) VALUES (?, ?, ?, ?, ?)",
        d,
    )

conn.commit()

# ── 打印出来看看 ────────────────────────────────────────
cur.execute("SELECT * FROM devices")
for row in cur.fetchall():
    print(row)

conn.close()
