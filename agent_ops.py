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
    {
        "type": "function",
        "function": {
            "name": "report_fault",
            "description": "报修一台设备，把它的状态改成故障。当用户说「XX 坏了」「XX 出故障了」「报修 XX」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "设备名，例如 核心交换机"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "warranty_status",
            "description": "查某台设备的保修到期日和是否过保。当用户问「XX 过保了吗」「XX 保修到什么时候」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "设备名，例如 核心交换机"}
                },
                "required": ["name"],
            },
        },
    },
]

# ★ 路由表：工具名 → HTTP 方法
methods = {
    "device_status": "get",
    "fault_count": "get",
    "expired_devices": "get",
    "device_count": "get",
    "report_fault": "post",
    "warranty_status": "get",
}

# ★ 想试别的问法，改这一行就行
QUESTION = "机房一共几台设备？"

MAX_ROUNDS = 10  # 保险丝：一个问题的工具调用最多转 10 轮

# 对话记录。一开始是空的，用户说什么就往里塞。
messages = []


def ask(question):
    """问一个问题，内部自己跑工具循环，最后返回它说的话"""
    messages.append({"role": "user", "content": question})

    round_num = 0
    while round_num < MAX_ROUNDS:
        round_num += 1
        print(f"\n──── 第 {round_num} 轮 ────")

        body = {"model": "deepseek-chat", "messages": messages, "tools": tools}
        message = requests.post(url, headers=headers, json=body).json()["choices"][0]["message"]

        messages.append(message)

        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return message["content"]

        print(f"① 它想调 {len(tool_calls)} 个工具")

        for tc in tool_calls:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            print(f"   ② 调 {name} | 参数 {args}")

            my_url = f"http://127.0.0.1:8001/{name}"
            method = methods[name]

            # 查：参数挂网址；改：参数装信封
            if method == "get":
                result = requests.request(method, my_url, params=args).json()
            else:
                result = requests.request(method, my_url, json=args).json()
            print(f"   ③ 接口回了：{result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return "（转太多轮了，我先停下，可能是接口一直出错）"


# ── 外层循环：一直等你说话 ────────────────────────────
while True:
    question = input("\n你问（输入 exit 退出）：")

    if question.strip() in ("exit", "quit", ""):
        print("再见。")
        break

    answer = ask(question)
    print(f"\n它答：{answer}")
