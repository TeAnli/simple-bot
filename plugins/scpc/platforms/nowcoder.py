import requests
from html import unescape
from json import loads
from typing import Optional, List
from bs4 import BeautifulSoup, Tag
from ..utils import Contest


def nowcoder_recent_contests_url() -> str:
    """
    返回获取牛客近期比赛页面的 URL（HTML 页面，非 JSON 接口）

    Returns:
    - 近期比赛页面的完整 URL 字符串
    """
    return f"https://ac.nowcoder.com/acm/contest/vip-index"


headers = {
    "Origin": "https://ac.nowcoder.com",
    "Referer": "https://ac.nowcoder.com/acm/contest/vip-index",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, text/plain, */*",
}


def get_nowcoder_recent_contests() -> Optional[List[Contest]]:
    """
    抓取牛客近期比赛页面并解析为结构化比赛列表

    Returns:
    - 解析得到的 `NowcoderContest` 列表若页面结构不符合预期或请求失败返回 None
    """
    try:
        response = requests.get(nowcoder_recent_contests_url(), headers=headers)
    except Exception:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    find_item = soup.find("div", class_="platform-mod js-current")
    if not isinstance(find_item, Tag):
        return None
    items: List[Contest] = []
    contest_table = find_item.find_all("div", class_="platform-item js-item")
    for contest in contest_table:
        data = loads(unescape(str(contest["data-json"])))
        id = unescape(str(contest["data-id"]))
        contest_url = f"https://ac.nowcoder.com/acm/contest/{id}"
        items.append(
            Contest(
                name=str(data["contestName"]),
                contest_id=int(id),
                start_ts=int(data["contestStartTime"] / 1000),
                duration_secs=int(data["contestDuration"] / 1000),
                url=contest_url,
            )
        )
    return items
