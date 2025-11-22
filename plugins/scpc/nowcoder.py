from html import unescape
from json import loads
from typing import Optional, List, Any, Union
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup, Tag


def nowcoder_recent_contests_url() -> str:
    """获取 牛客 最近比赛列表的 URL (HTML文本数据, 非JSON)"""
    return f'https://ac.nowcoder.com/acm/contest/vip-index'

@dataclass
class NowcoderContest:
    name: str
    startTime: str
    duration: int
    contest_url: str
    id: int


def get_nowcoder_recent_contests() -> Optional[List[NowcoderContest]]:
    headers = {
        'Origin': 'https://ac.nowcoder.com',
        'Referer': 'https://ac.nowcoder.com/acm/contest/vip-index',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/plain, */*',
    }
    try:
        response = requests.get(nowcoder_recent_contests_url(), headers=headers)
    except Exception as e:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    find_item = soup.find('div', class_='platform-mod js-current')
    if not isinstance(find_item, Tag):
        return None
    items = []
    datatable = find_item.find_all('div', class_='platform-item js-item')
    for contest in datatable:
        cdata = loads(unescape(contest.get("data-json")))
        id = unescape(contest.get("data-id"))
        cdata["contestId"] = id
        contest_url = f"https://ac.nowcoder.com/acm/contest/{cdata['contestId']}"
        if cdata:
            items.append(
                NowcoderContest(
                    id=id,
                    name=cdata['contestName'],
                    startTime=int(cdata["contestStartTime"] / 1000),
                    contest_url=contest_url,
                    duration=cdata["contestDuration"] / 1000
                )
            )
    return items
