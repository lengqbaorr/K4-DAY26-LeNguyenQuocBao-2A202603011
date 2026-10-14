"""Function Calling thuần với OpenAI GPT-4o và weather tool chạy trong app."""

import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

import os
import sys
import json
import unicodedata
import httpx
from dotenv import load_dotenv, find_dotenv

# Đảm bảo in tiếng Việt trên console Windows không bị lỗi UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(find_dotenv(usecwd=True))

from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else genai.Client()

MODEL = "gemini-3.8-flash"

MODEL = "gpt-4o"
SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp. Tóm tắt ngắn gọn và đưa lời khuyên thực tế."
)

# 1. App tự định nghĩa schema của các tools
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

get_forecast_3days_declaration = types.FunctionDeclaration(
    name="get_forecast_3days",
    description="Lấy dự báo thời tiết chi tiết qua 3 ngày tới của một thành phố từ API thời tiết thật (WeatherAPI)",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố (ví dụ: Hà Nội, Hồ Chí Minh, Đà Nẵng, Tokyo...)"
            )
        },
        required=["city"],
    ),
)

TOOLS = [
    types.Tool(
        function_declarations=[
            get_weather_declaration,
            get_forecast_3days_declaration,
        ]
    )
]


# 2. App tự thực thi tool (hàm mock và hàm gọi API thật)
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


def normalize_city_name(city: str) -> str:
    """Chuẩn hóa tên thành phố có dấu tiếng Việt sang không dấu để WeatherAPI tìm kiếm chính xác."""
    city_clean = city.replace("đ", "d").replace("Đ", "D")
    return "".join(
        c for c in unicodedata.normalize("NFD", city_clean)
        if unicodedata.category(c) != "Mn"
    )


def get_forecast_3days(city: str) -> str:
    """Lấy dự báo thời tiết 3 ngày tới sử dụng API thời tiết thật (WeatherAPI.com)."""
    weather_key = os.getenv("WEATHERAPI_KEY")
    if not weather_key:
        return json.dumps(
            {"error": "Chưa cấu hình WEATHERAPI_KEY trong file .env"},
            ensure_ascii=False,
        )

    # Chuẩn hoá tên thành phố để WeatherAPI tìm kiếm chính xác (vd: 'Hà Nội' -> 'Ha Noi')
    query_city = normalize_city_name(city)
    url = "https://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": weather_key,
        "q": query_city,
        "days": 3,
        "aqi": "no",
        "alerts": "no",
        "lang": "vi",  # Nhận mô tả thời tiết trực tiếp bằng tiếng Việt
    }

    try:
        with httpx.Client(timeout=10.0) as http_client:
            resp = http_client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        location = data.get("location", {})
        forecast_days = data.get("forecast", {}).get("forecastday", [])

        days_summary = []
        for day in forecast_days:
            day_info = day.get("day", {})
            days_summary.append({
                "ngay": day.get("date"),
                "nhiet_do_cao_nhat": f"{day_info.get('maxtemp_c')}°C",
                "nhiet_do_thap_nhat": f"{day_info.get('mintemp_c')}°C",
                "nhiet_do_trung_binh": f"{day_info.get('avgtemp_c')}°C",
                "thoi_tiet": day_info.get("condition", {}).get("text"),
                "xac_suat_mua": f"{day_info.get('daily_chance_of_rain')}%",
                "do_am_trung_binh": f"{day_info.get('avghumidity')}%",
                "gio_toi_da": f"{day_info.get('maxwind_kph')} km/h",
                "chi_so_uv": day_info.get("uv"),
            })

        result = {
            "thanh_pho": location.get("name"),
            "quoc_gia": location.get("country"),
            "du_bao_3_ngay": days_summary,
        }
        return json.dumps(result, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"Lỗi HTTP {e.response.status_code}: Không thể lấy dữ liệu cho {city}"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {"error": f"Lỗi kết nối WeatherAPI: {str(e)}"},
            ensure_ascii=False,
        )


TOOL_MAP = {
    "get_weather": get_weather,
    "get_forecast_3days": get_forecast_3days,
}


def run(prompt: str) -> str:
    """Để model chọn tool, app thực thi tool, rồi model tổng hợp câu trả lời."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = OpenAI()
    input_items = [{"role": "user", "content": prompt}]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    while resp.function_calls:
        # Thêm phản hồi của model vào lịch sử hội thoại
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            func = TOOL_MAP.get(fc.name)
            if func:
                result = func(**fc.args)  # <-- app chạy, không phải model
            else:
                result = json.dumps({"error": f"Tool {fc.name} không tồn tại"}, ensure_ascii=False)
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))
        resp = client.models.generate_content(
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
    question = "Dự báo thời tiết 3 ngày tới ở Hà Nội như thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:", run(question))

