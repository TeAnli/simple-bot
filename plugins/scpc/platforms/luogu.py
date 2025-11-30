from dataclasses import dataclass
import time
from typing import List, Optional
from ..utils import Contest, fetch_json


def luogu_contest_url() -> str:
    """
    获取洛谷比赛列表 API
    """
    return f"https://www.luogu.com.cn/contest/list?_contentOnly=1"


def get_luogu_contest() -> Optional[List[Contest]]:
    data = fetch_json(luogu_contest_url(), timeout=10)
    if data is None:
        return None
    contests_data = data["currentData"]["contests"]["result"]
    contests = []
    print(contests_data)
    for contest_data in contests_data:
        contest = Contest(
            name=contest_data.get("name", ""),
            contest_id=contest_data.get("id", 0),
            start_ts=contest_data.get("startTime", 0),
            duration_secs=int(contest_data.get("endTime", 0) - contest_data.get("startTime", 0)),
            url=f"https://www.luogu.com.cn/contest/{contest_data.get("id", 0)}",
        )
        contests.append(contest)
    print(contests)
    return contests
