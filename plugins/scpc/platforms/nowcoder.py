from html import unescape
from json import loads
from typing import List
from bs4 import BeautifulSoup, Tag

from plugins.scpc.platforms.platform import Platform, Contest
from plugins.scpc.utils.network import fetch_html


def nowcoder_recent_contests_url() -> str:
    """
    返回获取牛客近期比赛页面的 URL (HTML 页面，非 JSON 接口)
    """
    return f"https://ac.nowcoder.com/acm/contest/vip-index"


NOWCODER_HEADER = {
    "Origin": "https://ac.nowcoder.com",
    "Referer": "https://ac.nowcoder.com/acm/contest/vip-index",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Connection": "close",
}


class NowcoderPlatform(Platform):

    async def get_contests(self) -> List[Contest]:
        content = await fetch_html(
            nowcoder_recent_contests_url(), headers=NOWCODER_HEADER
        )
        soup = BeautifulSoup(content, "html.parser")
        find_item = soup.find("div", class_="platform-mod js-current")
        contests: List[Contest] = []
        if not isinstance(find_item, Tag):
            return contests
        contest_table = find_item.find_all("div", class_="platform-item js-item")
        for contest in contest_table:
            data = loads(unescape(str(contest["data-json"])))
            unescape_id = unescape(str(contest["data-id"]))
            contests.append(
                Contest(
                    name=str(data.get("contestName", "")),
                    id=int(unescape_id),
                    start_time=int(data.get("contestStartTime", 0) / 1000),
                    duration=int(data.get("contestDuration", 0) / 1000),
                    url=f"https://ac.nowcoder.com/acm/contest/{unescape_id}",
                )
            )
        return contests
