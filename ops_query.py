"""三个查询 —— 正好对应值班员最常问的三句话

Python 部分（连接、执行、取值、打印）我全写好了。
你只填空，每个空是一条 SQL。
"""

import sqlite3

conn = sqlite3.connect("ops.db")
cur = conn.cursor()


# ────────────────────────────────────────────────────────
#  ① 这个我填好了，当例子看
# ────────────────────────────────────────────────────────
def device_status(name):
    """核心交换机现在什么状态？ —— 按设备名查它的位置和状态"""
    sql = """
        SELECT location, status FROM devices WHERE name = ?
    """
    cur.execute(sql, (name,))
    return cur.fetchone()


# ────────────────────────────────────────────────────────
#  ② 这个你填：数一数有几台是故障
# ────────────────────────────────────────────────────────
def fault_count():
    """现在有几台设备是故障状态？ —— 只返回一个数字"""
    sql = """
        SELECT COUNT(*) FROM devices WHERE status = '故障'
    """
    cur.execute(sql)
    row = cur.fetchone()
    return row[0]


# ────────────────────────────────────────────────────────
#  ③ 这个先放着，等下再说
# ────────────────────────────────────────────────────────
def expired_devices():
    """哪些设备过保了？ —— 保修到期日早于今天的那些

    提示：SQLite 里「今天」的写法是 date('now')，
         它和 warranty_end 都是 'YYYY-MM-DD' 格式，可以直接比大小。
    """
    sql = """
        SELECT name, warranty_end FROM devices WHERE warranty_end < date('now')
    """
    cur.execute(sql)
    return cur.fetchall()


if __name__ == "__main__":
    print("① 核心交换机：", device_status("核心交换机"))
    print("② 故障设备台数：", fault_count())
    print("③ 过保设备：", expired_devices())
