from typing import Optional, List, Any
from dataclasses import dataclass
from ..utils import fetch_json
from ..utils import parse_scpc_time
from ..utils import Contest

import requests


def scpc_user_info_url(username: str) -> str:
    """
    返回查询 SCPC 用户主页信息的 API 地址

    Args:
    - username: SCPC 用户名
    """
    return f"http://scpc.fun/api/get-user-home-info?username={username}"


def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    """
    返回查询 SCPC 比赛列表的 API 地址

    Args:
    - current_page: 页码，从 0 开始
    - limit: 每页条目数
    """
    return (
        f"http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}"
    )


def scpc_recent_contest() -> str:
    """
    返回查询 SCPC 近期比赛的 API 地址
    """
    return f"http://scpc.fun/api/get-recent-contest"


def scpc_recent_updated_problem():
    """
    返回查询 SCPC 近期更新题目的 API 地址
    """
    return f"http://scpc.fun/api/get-recent-updated-problem"


def scpc_recent_ac_rank():
    """
    返回查询 SCPC 最近一周过题排行的 API 地址
    """
    return f"http://scpc.fun/api/get-recent-seven-ac-rank"


def scpc_login_url() -> str:
    """
    返回 SCPC 登录接口的 API 地址
    """
    return f"http://scpc.fun/api/login"


@dataclass
class ScpcUser:
    total: int  # 总提交数
    solved_list: List[Any]  # 通过题目列表
    nickname: str  # 昵称
    signature: str  # 个性签名


@dataclass
class ScpcWeekACUser:
    username: str  # 用户名
    avatar: str  # 头像地址
    title_name: str  # 头衔名称
    title_color: str  # 16进制RGB
    ac: int  # 通过题目数量


@dataclass
class ScpcContestRankUser:
    rank: int  # 排名
    award_name: str  # 奖项名称
    uid: str  # 用户 ID
    username: str  # 用户名
    real_name: str  # 真实姓名
    gender: str  # 性别
    avatar: str  # 头像地址
    total: int  # 总提交数
    ac: int  # 通过题目数量
    total_time: int  # 总耗时（秒）


@dataclass
class ScpcUpdatedProblem:
    id: int  # 记录 ID
    problem_id: str  # 题目 ID
    title: str  # 题目标题
    type: int  # 题目类型
    gmt_create: int  # 创建时间戳
    gmt_modified: int  # 修改时间戳
    url: str  # 题目页面链接


def scpc_login(username: str, password: str) -> Optional[str]:
    """
    登录 SCPC 并返回授权 Token

    Args:
    - username: 用户名
    - password: 密码

    Returns:
    - 授权 Token登录失败返回 None
    """
    response = requests.post(
        scpc_login_url(),
        headers={
            "Content-Type": "application/json",
            "Host": "scpc.fun",
            "Origin": "http://scpc.fun",
            "Referer": "http://scpc.fun/home",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        },
        json={
            "password": password,
            "username": username,
        },
    )
    if response.status_code != 200:
        return None
    return response.headers.get("Authorization")


def get_scpc_contest_rank(
    contest_id: int,
    token: str,
    current_page: int = 1,
    limit: int = 50,
) -> Optional[List[ScpcContestRankUser]]:
    """
    获取指定比赛的过题排行榜

    Args:
    - contest_id: 比赛 ID
    - token: 授权 Token
    - current_page: 页码
    - limit: 每页条目数

    Returns:
    - `ScpcContestRankUser` 列表请求失败或解析失败返回 None
    """
    response = requests.post(
        "http://scpc.fun/api/get-contest-rank",
        headers={
            "Content-Type": "application/json",
            "Host": "scpc.fun",
            "Origin": "http://scpc.fun",
            "Referer": "http://scpc.fun/home",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Authorization": token,
        },
        json={
            "currentPage": current_page,
            "limit": limit,
            "cid": contest_id,
            "forceRefresh": False,
            "removeStar": False,
            "concernedList": [],
            "keyword": None,
            "containsEnd": False,
            "time": None,
        },
    )
    if response.status_code != 200:
        return None
    try:
        json_data = response.json()
    except Exception:
        return None

    records = json_data.get("data", {}).get("records") or json_data.get("records") or []
    rank_users: List[ScpcContestRankUser] = []
    for record in records:
        try:
            rank_users.append(
                ScpcContestRankUser(
                    rank=int(record.get("rank", 0)),
                    award_name=str(record.get("awardName", "") or ""),
                    uid=str(record.get("uid", "") or ""),
                    username=str(record.get("username", "") or ""),
                    real_name=str(record.get("realname", "") or ""),
                    gender=str(record.get("gender", "") or ""),
                    avatar=str(record.get("avatar", "") or ""),
                    total=int(record.get("total", 0)),
                    ac=int(record.get("ac", 0)),
                    total_time=int(record.get("totalTime", 0)),
                )
            )
        except Exception:
            continue
    return rank_users


def get_scpc_rank() -> Optional[List[ScpcWeekACUser]]:
    """
    获取 SCPC 最近一周过题排行列表

    返回:
    - `ScpcWeekACUser` 列表失败返回 None
    """
    json_data = fetch_json(scpc_recent_ac_rank())
    if not json_data or "data" not in json_data:
        return None
    records = json_data.get("data") or []
    users: List[ScpcWeekACUser] = []
    for entry in records:
        try:
            username = entry.get("username") or ""
            avatar = entry.get("avatar") or ""
            title_name = entry.get("titlename") or ""
            title_color = entry.get("titleColor") or ""
            ac = int(entry.get("ac", 0))
            users.append(
                ScpcWeekACUser(
                    username=username,
                    avatar=avatar,
                    title_name=title_name,
                    title_color=title_color,
                    ac=ac,
                )
            )
        except Exception:
            continue
    return users


def get_scpc_user_info(username: str) -> Optional[ScpcUser]:
    """
    获取 SCPC 用户主页信息并解析为 `ScpcUser`

    Args:
    - username: 用户名
    """
    json_data = fetch_json(scpc_user_info_url(username))
    if not json_data or "data" not in json_data:
        return None
    data_obj = json_data.get("data") or {}
    total = int(data_obj.get("total", 0))
    solved = data_obj.get("solvedList") or []
    nickname = str(data_obj.get("nickname") or username)
    signature = str(data_obj.get("signature") or "")
    return ScpcUser(
        total=total, solved_list=solved, nickname=nickname, signature=signature
    )


def get_scpc_contests(
    current_page: int = 0, limit: int = 10
) -> Optional[List[Contest]]:
    """
    获取 SCPC 比赛列表并直接返回统一 `Contest` 列表
    """
    json_data = fetch_json(scpc_contests_url(current_page, limit))
    if not json_data:
        return None
    records = json_data.get("data", {}).get("records") or json_data.get("records") or []
    contests: List[Contest] = []
    for record in records:
        try:
            name = record.get("title") or record.get("contestName") or "未命名比赛"
            start_time = record.get("startTime")
            duration_secs = int(record.get("duration") or 0)
            cid = int(
                record.get("id") or record.get("contestId") or record.get("cid") or 0
            )
            url = f"http://scpc.fun/contest/{cid}" if cid else "http://scpc.fun/contest"
            contests.append(
                Contest(
                    name=str(name),
                    contest_id=cid,
                    start_ts=parse_scpc_time(start_time),
                    duration_secs=duration_secs,
                    url=url,
                )
            )
        except Exception:
            continue
    return contests


def get_scpc_recent_contests() -> Optional[List[Contest]]:
    """
    获取 SCPC 近期比赛并直接返回统一 `Contest` 列表
    """
    json_data = fetch_json(scpc_recent_contest())
    if not json_data:
        return None
    records = json_data.get("data") or []
    contest_list: List[Contest] = []
    for record in records:
        try:
            name = str(record.get("title") or "未命名比赛")
            start_time = record.get("startTime")
            duration_secs = int(record.get("duration") or 0)
            cid = int(
                record.get("id") or record.get("contestId") or record.get("cid") or 0
            )
            url = f"http://scpc.fun/contest/{cid}" if cid else "http://scpc.fun/contest"
            contest_list.append(
                Contest(
                    name=name,
                    contest_id=cid,
                    start_ts=parse_scpc_time(start_time),
                    duration_secs=duration_secs,
                    url=url,
                )
            )
        except Exception:
            continue
    return contest_list


def get_scpc_recent_updated_problems() -> Optional[List[ScpcUpdatedProblem]]:
    """
    获取 SCPC 近期更新题目并解析为 `ScpcUpdatedProblem` 列表

    Returns:
    - `ScpcUpdatedProblem` 列表失败返回 None
    """
    body = fetch_json(scpc_recent_updated_problem())
    if not body:
        return None
    raw = body.get("data") or []
    items: List[ScpcUpdatedProblem] = []
    for r in raw:
        try:
            rid = int(r.get("id", 0))
            pid = str(r.get("problemId", "") or "")
            title = str(r.get("title", "") or "")
            typ = int(r.get("type", 0))
            created = parse_scpc_time(r.get("gmtCreate"))
            modified = parse_scpc_time(r.get("gmtModified"))
            url = f"http://scpc.fun/problem/{pid}" if pid else "http://scpc.fun/problem"
            items.append(
                ScpcUpdatedProblem(
                    id=rid,
                    problem_id=pid,
                    title=title,
                    type=typ,
                    gmt_create=created,
                    gmt_modified=modified,
                    url=url,
                )
            )
        except Exception:
            continue
    return items
