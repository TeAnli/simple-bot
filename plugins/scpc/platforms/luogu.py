from typing import List, Optional
from ..utils import Contest, fetch_json


def luogu_contest_url() -> str:
    """
    获取洛谷比赛列表 API
    """
    return f"https://www.luogu.com.cn/contest/list?_contentOnly=1"


def get_luogu_contest() -> Optional[List[Contest]]:
    response = fetch_json(luogu_contest_url())
    if response is None:
        return None
    records = response["currentData"]["contests"]["result"]
    contests = []
    for entry in records:
        contest = Contest(
            name=str(entry.get("name", "")),
            contest_id=int(entry.get("id", 0)),
            start_ts=int(entry.get("startTime", 0)),
            duration_secs=int(entry.get("endTime", 0) - entry.get("startTime", 0)),
            url=f"https://www.luogu.com.cn/contest/{int(entry.get("id", 0))}",
        )
        contests.append(contest)
    return contests
