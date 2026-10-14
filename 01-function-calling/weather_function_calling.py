"""Function Calling thuần với OpenAI GPT-4o và weather tool chạy trong app."""

import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


MODEL = "gpt-4o"
SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp. Tóm tắt ngắn gọn và đưa lời khuyên thực tế."
)

# Schema phải được viết tay và giữ khớp với hàm get_weather bên dưới.
TOOLS = [{
    "type": "function",
    "name": "get_weather",
    "description": "Lấy thời tiết hiện tại của một thành phố",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string", "description": "Tên thành phố"}},
        "required": ["city"],
        "additionalProperties": False,
    },
    "strict": True,
}]


def get_weather(city: str) -> str:
    """Trả về thời tiết giả lập của thành phố để minh họa function calling."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C", "thời_tiết": "trời mưa nhẹ", "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C", "thời_tiết": "mưa rào", "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C", "thời_tiết": "nhiều mây", "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }
    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def run(prompt: str) -> str:
    """Để model chọn tool, app thực thi tool, rồi model tổng hợp câu trả lời."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = OpenAI()
    input_items = [{"role": "user", "content": prompt}]

    for _ in range(5):
        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_INSTRUCTION,
            input=input_items,
            tools=TOOLS,
        )
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return response.output_text

        input_items.extend(response.output)
        for call in calls:
            if call.name != "get_weather":
                raise ValueError(f"Unsupported function: {call.name}")
            args = json.loads(call.arguments)
            print(f"  [model yêu cầu] {call.name}({args})")
            result = get_weather(**args)  # App chạy hàm, model không chạy.
            print(f"  [app thực thi]  -> {result}")
            input_items.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": result,
            })

    raise RuntimeError("Model exceeded the maximum number of tool-call rounds")


if __name__ == "__main__":
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:", run(question))
