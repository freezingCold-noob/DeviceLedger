"""演示：每一轮，我们到底递给 AI 什么

这个文件只干一件事 —— 把 messages 打印出来。
看懂这个，就懂为什么要转两轮了。
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

tools = [
    {
        "type": "function",
        "function": {
            "name": "device_status",
            "description": "查询某一台设备的位置和当前状态",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "设备名"}},
                "required": ["name"],
            },
        },
    }
]

# 一开始，纸上只有一句话
messages = [{"role": "user", "content": "核心交换机和 UPS 电源现在分别是什么状态？"}]


def print_paper(round_no):
    print(f"\n{'=' * 56}")
    print(f"  第 {round_no} 轮：我递给它的纸上，一共 {len(messages)} 条")
    print("=" * 56)
    for i, m in enumerate(messages):
        role = m.get("role")
        if role == "user":
            print(f"  [{i}] 用户说：{m['content']}")
        elif role == "assistant":
            print(f"  [{i}] 它上轮说：我要调 {len(m['tool_calls'])} 个工具")
        elif role == "tool":
            print(f"  [{i}] 工具结果：{m['content']}")


for round_no in range(1, 5):
    print_paper(round_no)

    body = {"model": "deepseek-chat", "messages": messages, "tools": tools}
    message = requests.post(url, headers=headers, json=body).json()["choices"][0]["message"]

    messages.append(message)

    tool_calls = message.get("tool_calls")

    if not tool_calls:
        print(f"\n>>> 它终于开口了：\n{message['content']}")
        break

    print(f"\n>>> 它的回复：我要调 {len(tool_calls)} 个工具")

    for tc in tool_calls:
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"])
        result = requests.get(f"http://127.0.0.1:8001/{name}", params=args).json()
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
