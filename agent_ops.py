"""机房设备运维助手 —— Agent 层

流程（和记账程序那套完全一样，只是换了工具）：
    ① 用户说一句话
    ② 大模型从工具清单里挑一个，填好参数
    ③ 我们照着名字去调自己的接口
    ④ 结果原样回传
    ⑤ 大模型说人话
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

url = "https://api.deepseek.com/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

# ★ 工具清单：工具名必须和 api_ops.py 里 @app.get("/xxx") 的 xxx 一模一样
tools = [
    {
        "type": "function",
        "function": {
            "name": "device_status",
            "description": "查询某一台设备的位置和当前状态（正常/故障）。当用户问「核心交换机怎么样了」「某台设备现在什么状态」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "设备名，例如 核心交换机、UPS 电源",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fault_count",
            "description": "统计当前有多少台设备处于故障状态。当用户问「有几台坏了」「故障设备有几台」时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expired_devices",
            "description": "列出所有已经过保的设备。当用户问「哪些设备过保了」「保修到期的有哪些」时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "device_count",
            "description": "统计机房一共有多少台设备",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# ★ 路由表：工具名 → HTTP 方法
methods = {
    "device_status": "get",
    "fault_count": "get",
    "expired_devices": "get",
    "device_count": "get",
}

# ★ 想试别的问法，改这一行就行
QUESTION = "机房一共几台设备？"

# ── 对话记录：从「用户说的第一句话」开始 ──────────────
messages = [{"role": "user", "content": QUESTION}]

round_num = 0
MAX_ROUNDS = 10  # 保险丝：最多转 10 轮，防止死循环

while round_num < MAX_ROUNDS:
    round_num += 1
    print(f"\n──── 第 {round_num} 轮 ────")

    # ① 问模型：接下来该干嘛？
    body = {"model": "deepseek-chat", "messages": messages, "tools": tools}
    message = requests.post(url, headers=headers, json=body).json()["choices"][0]["message"]

    # 它这条回复要记进历史（里面有 tool_calls）
    messages.append(message)

    tool_calls = message.get("tool_calls")

    # ② 它不要工具了 → 说明它准备说人话了 → 结束循环
    if not tool_calls:
        print("⑥ 它说：")
        print(message["content"])
        break

    # ③ 它要工具：可能一个，也可能好几个，全都执行
    print(f"① 它想调 {len(tool_calls)} 个工具")

    for tc in tool_calls:
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"])
        print(f"   ② 调 {name} | 参数 {args}")

        my_url = f"http://127.0.0.1:8001/{name}"
        result = requests.request(methods[name], my_url, params=args).json()
        print(f"   ③ 接口回了：{result}")

        # ④ 把结果一条一条塞回历史，一个 tool_call 配一条结果
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
    # 循环回去，再问一次模型

else:
    # while 后面这个 else：只有「没走 break」才会执行到这里
    print(f"⚠️ 转满 {MAX_ROUNDS} 轮还没结束，强制停止（多半是工具一直报错，它在反复重试）")
