"""机房设备运维助手 —— 接口层

三个接口，正好对应值班员最常问的三句话。
接口名 = 网址最后那一截，等下 Agent 里的工具名要和这里一一对应。
"""

import sqlite3

from fastapi import FastAPI

app = FastAPI()

DB = "ops.db"


def query(sql, params=()):
    """开库 → 执行 → 取结果 → 关库，四步封装成一个函数"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/device_status")
def device_status(name: str):
    """值班员问：核心交换机现在什么状态？"""
    rows = query("SELECT location, status FROM devices WHERE name = ?", (name,))
    if not rows:
        # 查不到就说查不到，不编造
        return {"found": False, "message": f"台账里没有叫「{name}」的设备"}
    return {
        "found": True,
        "name": name,
        "location": rows[0][0],
        "status": rows[0][1],
    }


@app.get("/fault_count")
def fault_count():
    """值班员问：现在有几台设备是故障状态？"""
    rows = query("SELECT COUNT(*) FROM devices WHERE status = '故障'")
    return {"fault_count": rows[0][0]}


@app.get("/expired_devices")
def expired_devices():
    """值班员问：哪些设备过保了？"""
    rows = query("SELECT name, warranty_end FROM devices WHERE warranty_end < date('now')")
    return {
        "count": len(rows),
        "devices": [{"name": r[0], "warranty_end": r[1]} for r in rows],
    }

@app.get("/device_count")
def device_count():
    rows = query("SELECT COUNT(*) FROM devices")
    return {"device_count": rows[0][0]}
