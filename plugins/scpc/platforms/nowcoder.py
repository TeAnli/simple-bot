import requests
from html import unescape
from json import loads
from typing import Optional, List
from bs4 import BeautifulSoup, Tag
from ..utils import Contest


def nowcoder_recent_contests_url() -> str:
    """
    返回获取牛客近期比赛页面的 URL（HTML 页面，非 JSON 接口）
    """
    return f"https://ac.nowcoder.com/acm/contest/vip-index"


headers = {
    "Origin": "https://ac.nowcoder.com",
    "Referer": "https://ac.nowcoder.com/acm/contest/vip-index",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, text/plain, */*",
}


def get_nowcoder_recent_contests() -> Optional[List[Contest]]:
    response = requests.get(nowcoder_recent_contests_url(), headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    find_item = soup.find("div", class_="platform-mod js-current")
    if not isinstance(find_item, Tag):
        return None
    items: List[Contest] = []
    contest_table = find_item.find_all("div", class_="platform-item js-item")
    for contest in contest_table:
        data = loads(unescape(str(contest["data-json"])))
        id = unescape(str(contest["data-id"]))
        items.append(
            Contest(
                name=str(data.get("contestName", "")),
                contest_id=int(id),
                start_ts=int(data.get("contestStartTime", 0) / 1000),
                duration_secs=int(data.get("contestDuration", 0) / 1000),
                url=f"https://ac.nowcoder.com/acm/contest/{id}",
            )
        )
    return items
