from typing import List

from plugins.scpc.platforms.platform import Platform, Contest
from plugins.scpc.utils.network import fetch_json


def luogu_contest_url() -> str:
    """
    获取洛谷比赛列表 API
    """
    return f"https://www.luogu.com.cn/contest/list?_contentOnly=1"


class LuoguPlatform(Platform):

    async def get_contests(self) -> List[Contest]:
        response = await fetch_json(luogu_contest_url())
        records = response["currentData"]["contests"]["result"]
        contests: List[Contest] = []
        for entry in records:
            contest = Contest(
                name=str(entry.get("name", "")),
                id=int(entry.get("id", 0)),
                start_time=int(entry.get("startTime", 0)),
                duration=int(entry.get("endTime", 0) - entry.get("startTime", 0)),
                url=f"https://www.luogu.com.cn/contest/{int(entry.get('id', 0))}",
            )
            contests.append(contest)
        return contests
