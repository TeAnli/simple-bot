from enum import Enum

from httpx import AsyncClient


class Method(Enum):
    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"


DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Connection": "close",
}


async def fetch_html(url: str, headers=None) -> str:
    """
    直接通过GET请求获取HTML文本信息

    Args:
        url: 目标url地址
        headers: HTTP请求头

    Returns:
        HTML文本信息
    """
    if headers is None:
        headers = DEFAULT_HEADERS

    async with AsyncClient() as client:
        response = await client.get(url=url, headers=headers)

    return response.text


async def fetch_json(
    url: str,
    headers: dict | None = None,
    payload: dict | None = None,
    method: Method = Method.GET,
) -> dict:
    """
    通过自定义请求获取请求数据

    Args:
        payload: 请求数据
        method: 请求方式
        url: 目标url地址
        headers: HTTP请求头

    Returns:
        JSON数据转义后的字典
    """
    if headers is None:
        headers = DEFAULT_HEADERS

    async with AsyncClient() as client:
        response = await client.request(
            url=url, json=payload, headers=headers, method=method.value
        )
    try:
        return response.json()
    except Exception as e:
        print(f"Error parsing JSON response from {url}: {e}")
        return {}
