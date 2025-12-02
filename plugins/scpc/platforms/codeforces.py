from typing import Optional, List
from dataclasses import dataclass
from ..utils import fetch_json, Contest


def codeforces_contests_url(include_gym: bool = False) -> str:
    """
    返回 Codeforces 比赛列表 API 的 URL

    Args:
    - include_gym: 是否包含 Gym 比赛，默认 False
    """
    return f"https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}"


def codeforces_user_rating_url(username: str) -> str:
    """
    返回指定用户的 rating 变更记录 API 的 URL

    Args:
    - username: Codeforces 用户名（handle）
    """
    return f"https://codeforces.com/api/user.rating?handle={username}"


@dataclass
class CodeforcesUserRating:
    contest_id: int  # 比赛ID
    contest_name: str  # 比赛名称
    handle: str  # 用户名
    new_rating: int  # 新评分
    old_rating: int  # 旧评分
    rating_update_time_seconds: int  # 评分更新时间（时间戳）


def get_codeforces_contests(include_gym: bool = False) -> Optional[List[Contest]]:
    response = fetch_json(codeforces_contests_url(include_gym))
    if not response or response.get("status") != "OK":
        return None
    records = response["result"]
    contests: List[Contest] = []
    for entry in records:
        contests.append(
            Contest(
                name=str(entry.get("name", "")),
                contest_id=int(entry.get("id", 0)),
                start_ts=int(entry.get("startTimeSeconds", 0)),
                duration_secs=int(entry.get("durationSeconds", 0)),
                url=(f"https://codeforces.com/contest/{int(entry.get("id", 0))}"),
            )
        )
    return contests


def get_codeforces_user_rating(handle: str) -> Optional[List[CodeforcesUserRating]]:
    response = fetch_json(codeforces_user_rating_url(handle))
    if not response or response.get("status") != "OK":
        return None
    records = response["result"]
    changes: List[CodeforcesUserRating] = []
    for entry in records:
        changes.append(
            CodeforcesUserRating(
                contest_id=int(entry.get("contestId", 0)),
                contest_name=str(entry.get("contestName", "")),
                handle=str(entry.get("handle", handle)),
                new_rating=int(entry.get("newRating", 0)),
                old_rating=int(entry.get("oldRating", 0)),
                rating_update_time_seconds=int(entry.get("ratingUpdateTimeSeconds", 0)),
            )
        )
    return changes
