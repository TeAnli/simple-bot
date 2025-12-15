from typing import List

from ncatbot.utils import get_log

from ..utils.network import fetch_json
from .platform import Contest, Platform

LOG = get_log()


def luogu_contest_url() -> str:
    """
    获取洛谷比赛列表 API
    """
    return f"https://www.luogu.com.cn/contest/list?_contentOnly=1"


class LuoguPlatform(Platform):

    async def get_contests(self) -> List[Contest]:
        try:
            response = await fetch_json(luogu_contest_url())
            if (
                not response
                or "currentData" not in response
                or "contests" not in response["currentData"]
            ):
                LOG.warning("Luogu API response format error")
                return []

            records = response["currentData"]["contests"].get("result", [])
            contests: List[Contest] = []
            for entry in records:
                start_time = int(entry.get("startTime", 0))
                end_time = int(entry.get("endTime", 0))
                contest = Contest(
                    name=str(entry.get("name", "")),
                    id=int(entry.get("id", 0)),
                    start_time=start_time,
                    duration=end_time - start_time,
                    url=f"https://www.luogu.com.cn/contest/{int(entry.get('id', 0))}",
                )
                contests.append(contest)
            return contests
        except Exception as e:
            LOG.error(f"Failed to get Luogu contests: {e}")
            return []
