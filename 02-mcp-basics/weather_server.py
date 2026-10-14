"""MCP SERVER minh hoạ — công bố tool `get_weather` qua giao thức MCP.

Khác với function calling: tool nằm ở một server ĐỘC LẬP. Server tự "khai
báo" tool của mình; bất kỳ MCP client nào (Claude Code, Claude Desktop,
Cursor, hoặc weather_client.py) cũng cắm vào dùng được mà không cần biết
code bên trong.

Schema của tool được TỰ ĐỘNG sinh ra từ type hints + docstring.

Chạy trực tiếp:
    pip install -r ../requirements.txt
    python weather_server.py

Đăng ký với Claude Code (làm 1 lần, dùng mãi):
    claude mcp add weather -- python /đường/dẫn/tới/weather_server.py
"""

import os
import httpx
from dotenv import load_dotenv, find_dotenv
from mcp.server.mcpserver import MCPServer

load_dotenv(find_dotenv(usecwd=True))

mcp = MCPServer("weather")

_MOCK_DB = {
    "Hanoi": "29°C, trời mưa",
    "Haiphong": "33°C, mưa rào",
    "Danang": "30°C, nhiều mây",
}


@mcp.tool()
def get_weather(city: str) -> str:
    """Lấy thời tiết hiện tại của một thành phố."""
    return f"{city}: {_MOCK_DB.get(city, '28°C, không có dữ liệu chi tiết')}"


@mcp.tool()
def get_forecast_3days(city: str) -> str:
    """Lấy dự báo thời tiết 3 ngày tới của một thành phố sử dụng WeatherAPI thật."""
    api_key = os.getenv("WEATHERAPI_KEY")
    if not api_key:
        return f"{city}: Cần cấu hình WEATHERAPI_KEY trong file .env để lấy dữ liệu thực tế."

    try:
        url = "https://api.weatherapi.com/v1/forecast.json"
        params = {"key": api_key, "q": city, "days": 3, "aqi": "no", "alerts": "no"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        forecast_lines = [
            f"- {d['date']}: {d['day']['condition']['text']}, nhiệt độ {d['day']['mintemp_c']}°C - {d['day']['maxtemp_c']}°C, xác suất mưa {d['day']['daily_chance_of_rain']}%"
            for d in data.get("forecast", {}).get("forecastday", [])
        ]
        loc = data.get("location", {})
        return f"Dự báo 3 ngày tới tại {loc.get('name')}, {loc.get('country')}:\n" + "\n".join(forecast_lines)
    except Exception as e:
        return f"Lỗi lấy dự báo 3 ngày cho {city}: {e}"


if __name__ == "__main__":
    mcp.run()  # mặc định chạy qua stdio
