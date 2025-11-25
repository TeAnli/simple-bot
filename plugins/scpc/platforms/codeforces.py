from typing import Optional, List
from dataclasses import dataclass
import requests
from ..utils import fetch_json, Contest


def codeforces_contests_url(include_gym: bool = False) -> str:
    """
    返回 Codeforces 比赛列表 API 的 URL

    Args:
    - include_gym: 是否包含 Gym 比赛，默认 False

    Returns:
    - 完整的查询 URL 字符串
    """
    return f"https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}"


def codeforces_user_rating_url(username: str) -> str:
    """
    返回指定用户的 rating 变更记录 API 的 URL

    Args:
    - username: Codeforces 用户名（handle）

    Returns:
    - 完整的查询 URL 字符串
    """
    return f"https://codeforces.com/api/user.rating?handle={username}"


@dataclass
class CodeforcesUserRatingChange:
    contest_id: int  # 比赛ID
    contest_name: str  # 比赛名称
    handle: str  # 用户名
    new_rating: int  # 新评分
    old_rating: int  # 旧评分
    rating_update_time_seconds: int  # 评分更新时间（时间戳）


def get_codeforces_contests(
    include_gym: bool = False, timeout: int = 10
) -> Optional[List[Contest]]:
    json_data = fetch_json(codeforces_contests_url(include_gym), timeout=timeout)
    if not json_data or json_data.get("status") != "OK":
        try:
            resp = requests.get(codeforces_contests_url(include_gym), timeout=timeout)
            if resp.status_code == 200:
                json_data = resp.json()
            else:
                return None
        except Exception:
            return None
        if not json_data or json_data.get("status") != "OK":
            return None
    records = json_data.get("result", [])
    contests: List[Contest] = []
    for entry in records:
        try:
            cid = int(entry.get("id", 0))
            contests.append(
                Contest(
                    name=str(entry.get("name", "")),
                    contest_id=cid,
                    start_ts=int(entry.get("startTimeSeconds", 0)),
                    duration_secs=int(entry.get("durationSeconds", 0)),
                    url=(
                        f"https://codeforces.com/contest/{cid}"
                        if cid
                        else "https://codeforces.com/contests"
                    ),
                )
            )
        except Exception:
            continue
    return contests


def get_codeforces_user_rating(
    handle: str, timeout: int = 10
) -> Optional[List[CodeforcesUserRatingChange]]:
    """
    请求并解析用户的 Codeforces rating 变更记录

    Args:
    - handle: 用户名 (handle)
    - timeout: 网络请求超时时间 (秒)

    Returns:
    - CodeforcesUserRatingChange 列表失败或状态不为 OK 时返回 None
    """
    json_data = fetch_json(codeforces_user_rating_url(handle), timeout=timeout)
    if not json_data or json_data.get("status") != "OK":
        return None
    records = json_data.get("result", [])
    changes: List[CodeforcesUserRatingChange] = []
    for entry in records:
        try:
            changes.append(
                CodeforcesUserRatingChange(
                    contest_id=int(entry.get("contestId", 0)),
                    contest_name=str(entry.get("contestName", "")),
                    handle=str(entry.get("handle", handle)),
                    new_rating=int(entry.get("newRating", 0)),
                    old_rating=int(entry.get("oldRating", 0)),
                    rating_update_time_seconds=int(
                        entry.get("ratingUpdateTimeSeconds", 0)
                    ),
                )
            )
        except Exception:
            continue
    return changes
