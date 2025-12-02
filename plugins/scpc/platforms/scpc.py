from typing import Optional, List, Any
from dataclasses import dataclass, fields

from httpx import AsyncClient
from playwright.async_api import async_playwright

import os
import xlsxwriter

from .platform import Platform, Contest
from ..utils.network import *
from ..utils.text import *


# ----------------------------
# region API URL 构建函数
# ----------------------------
def scpc_user_info_url(username: str) -> str:
    """
    返回查询 SCPC 用户主页信息的 API'

    Args:
        username: SCPC 用户名
    """
    return f"http://scpc.fun/api/get-user-home-info?username={username}"


def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    """
    返回查询 SCPC 比赛列表的 API'

    Args:
        current_page: 页码，从 0 开始
        limit: 每页条目数
    """
    return (
        f"http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}"
    )


def scpc_recent_contest_url() -> str:
    """
    返回查询 SCPC 近期比赛的 API'
    """
    return f"http://scpc.fun/api/get-recent-contest"


def scpc_recent_updated_problem_url():
    """
    返回查询 SCPC 近期更新题目的 API'
    """
    return f"http://scpc.fun/api/get-recent-updated-problem"


def scpc_recent_ac_rank_url():
    """
    返回查询 SCPC 最近一周过题排行的 API'
    """
    return f"http://scpc.fun/api/get-recent-seven-ac-rank"


def scpc_login_url() -> str:
    """
    返回 SCPC 登录接口的 API'
    """
    return f"http://scpc.fun/api/login"


def scpc_contest_rank() -> str:
    """
    获取 SCPC 比赛排行榜 API
    """
    return f"http://scpc.fun/api/get-contest-rank"


# ----------------------------
# region 数据类定义
# ----------------------------
@dataclass
class ScpcUser:
    total: int  # 总提交数
    solved_list: List[Any]  # 通过题目列表
    nickname: str  # 昵称
    signature: str  # 个性签名
    avatar: str  # 头像地址


@dataclass
class ScpcWeekACUser:
    username: str  # 用户名
    avatar: str  # 头像地址
    title_name: str  # 头衔名称
    title_color: str  # 16进制RGB
    ac: int  # 通过题目数量


@dataclass
class ACMInformation:
    error_count: int
    is_ac: bool = False
    ac_time: int = 0
    is_first_ac: bool = False


@dataclass
class ScpcContestRankUser:
    rank: int  # 排名
    award_name: str  # 奖项名称
    user_name: str  # 用户名
    real_name: str  # 真实姓名
    nick_name: str  # 昵称
    school: str  # 班级
    total: int  # 总尝试次数
    total_time: int  # 总耗时
    ac: int  # 通过题目数量
    information: dict[int, ACMInformation]  # 题目提交信息，键为题目ID

    @classmethod
    def get_chinese_headers(cls) -> dict[str, str]:
        return {
            "rank": "排名",
            "award_name": "奖项",
            "user_name": "用户名",
            "real_name": "真实姓名",
            "nick_name": "昵称",
            "school": "班级",
            "total_time": "耗时",
            "total": "总尝试次数",
            "ac": "通过数",
        }


@dataclass
class ScpcUpdatedProblem:
    id: int  # 记录 ID
    problem_id: str  # 题目 ID
    title: str  # 题目标题
    type: int  # 题目类型
    gmt_create: int  # 创建时间戳
    gmt_modified: int  # 修改时间戳
    url: str  # 题目页面链接


class SCPCPlatform(Platform):

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.token = None

    async def login(self):
        async with AsyncClient() as client:
            response = await client.post(
                scpc_login_url(),
                headers={
                    "Host": "scpc.fun",
                    "Origin": "http://scpc.fun",
                    "Referer": "http://scpc.fun/home",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
                    "Connection": "close",
                },
                json={
                    "password": self.password,
                    "username": self.username,
                },
            )
        self.token = response.headers["Authorization"]

    async def get_contest_rank(self, contest_id: int) -> List[ScpcContestRankUser]:
        response = await fetch_json(
            scpc_contest_rank(),
            method=Method.POST,
            headers={
                "Content-Type": "application/json",
                "Host": "scpc.fun",
                "Origin": "http://scpc.fun",
                "Referer": "http://scpc.fun/home",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "Authorization": self.token,
            },
            payload={
                "currentPage": 0,
                "limit": 999999,
                "cid": contest_id,
                "forceRefresh": False,
                "removeStar": False,
                "concernedList": [],
                "keyword": None,
                "containsEnd": False,
                "time": None,
            },
        )
        records = (
            response.get("data", {}).get("records") or response.get("records") or []
        )
        rank_users: List[ScpcContestRankUser] = []
        for entry in records:
            submission_info = {}
            for data in entry["submissionInfo"]:
                information = entry["submissionInfo"][data]
                submission_info[data] = ACMInformation(
                    ac_time=int(information.get("ACTime", 0)),
                    is_ac=bool(information.get("isAC", False)),
                    error_count=int(information.get("errorNum", 0)),
                    is_first_ac=bool(information.get("isFirstAC", False)),
                )
            rank_users.append(
                ScpcContestRankUser(
                    rank=int(entry.get("rank", 0)),
                    award_name=str(entry.get("awardName", "")),
                    user_name=str(entry.get("username", "")),
                    real_name=str(entry.get("realname", "")),
                    nick_name=str(entry.get("nickname", "")),
                    school=str(entry.get("school", "")),
                    total=int(entry.get("total", 0)),
                    ac=int(entry.get("ac", 0)),
                    total_time=int(entry.get("totalTime", 0)),
                    information=submission_info,
                )
            )
        print(rank_users)
        return rank_users

    async def get_week_rank(self) -> List[ScpcWeekACUser]:
        response = await fetch_json(scpc_recent_ac_rank_url())
        records = response["data"]
        users: List[ScpcWeekACUser] = []
        for entry in records:
            users.append(
                ScpcWeekACUser(
                    username=str(entry.get("username", "")),
                    avatar="http://scpc.fun" + str(entry.get("avatar", "")),
                    title_name=str(entry.get("titleName", "")),
                    title_color=str(entry.get("titleColor", "")),
                    ac=int(entry.get("ac", 0)),
                )
            )
        return users

    async def get_user_info(self, username: str) -> ScpcUser:
        response = await fetch_json(scpc_user_info_url(username))
        data_obj = response.get("data") or {}
        total = int(data_obj.get("total", 0))
        solved = data_obj.get("solvedList") or []
        nickname = str(data_obj.get("nickname") or username)
        signature = str(data_obj.get("signature"))
        avatar_val = str(data_obj.get("avatar", ""))
        if avatar_val and not avatar_val.startswith("http"):
            avatar_val = (
                "http://scpc.fun" + avatar_val
                if avatar_val.startswith("/")
                else "http://scpc.fun/" + avatar_val
            )
        return ScpcUser(
            total=total,
            solved_list=solved,
            nickname=nickname,
            signature=signature,
            avatar=avatar_val,
        )

    async def get_recent_contests(self) -> Optional[List[Contest]]:
        """
        获取 SCPC 近期比赛并直接返回统一 `Contest` 列表
        """
        response = await fetch_json(scpc_recent_contest_url())
        if not response or "data" not in response:
            return None
        records = response.get("data") or []
        contest_list: List[Contest] = []
        for record in records:
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
                    id=cid,
                    start_time=parse_scpc_time(start_time),
                    duration=duration_secs,
                    url=url,
                )
            )
        return contest_list

    async def get_recent_updated_problems(self) -> List[ScpcUpdatedProblem]:
        response = await fetch_json(scpc_recent_updated_problem_url())
        records = response.get("data") or []
        problems: List[ScpcUpdatedProblem] = []
        for entry in records:
            problems.append(
                ScpcUpdatedProblem(
                    id=int(entry.get("id", 0)),
                    problem_id=str(entry.get("problemId", "")),
                    title=str(entry.get("title", "")),
                    type=int(entry.get("type", 0)),
                    gmt_create=parse_scpc_time(entry.get("gmtCreate")),
                    gmt_modified=parse_scpc_time(entry.get("gmtModified")),
                    url=f"http://scpc.fun/problem/{entry.get('problemId', '')}",
                )
            )
        return problems

    async def get_contests(self) -> List[Contest]:
        json_data = await fetch_json(scpc_contests_url())
        records = (
            json_data.get("data", {}).get("records") or json_data.get("records") or []
        )
        contests: List[Contest] = []
        for record in records:
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
                    id=cid,
                    start_time=parse_scpc_time(start_time),
                    duration=duration_secs,
                    url=url,
                )
            )
        return contests


# ----------------------------
# region 核心功能函数
# ----------------------------


async def render_scpc_week_rank_image(users: list) -> str | None:
    try:

        def hex_to_rgb_str(h: str, default: str = "0,150,60"):
            h = (h).strip().lstrip("#")
            if len(h) == 6:
                try:
                    r = int(h[0:2], 16)
                    g = int(h[2:4], 16)
                    b = int(h[4:6], 16)
                    return f"{r},{g},{b}"
                except Exception:
                    return default
            return default

        rows = []
        for i, u in enumerate(users, start=1):
            title_rgb = hex_to_rgb_str(getattr(u, "title_color", ""))
            title_name = getattr(u, "title_name", "")
            username = getattr(u, "username", "")
            avatar = getattr(u, "avatar", "")
            ac = int(getattr(u, "ac", 0))
            rank_color = (
                "#FFD700"
                if i == 1
                else ("#C0C0C0" if i == 2 else ("#CD7F32" if i == 3 else "#64A5FF"))
            )
            pill_html = (
                ""
                if not title_name
                else f"<div class='pill' style='color:rgb({title_rgb});border-color:rgb({title_rgb});background:rgba({title_rgb},0.12)'>{title_name}</div>"
            )
            rows.append(
                f"""
                <div class='row'>
                  <div class='rank' style='background:{rank_color}'>{i}</div>
                  <div class='avatar-wrap'>
                    <img class='avatar' src='{avatar}' onerror="this.style.display='none'; this.parentNode.classList.add('fallback')"/>
                    <div class='avatar-fallback'>{(username[:1] or ' ').upper()}</div>
                  </div>
                  <div class='user'><span class='username'>{username}</span>{pill_html}</div>
                  <div class='ac'>AC {ac}</div>
                </div>
                """
            )
        html = f"""
        <html>
          <head>
            <meta charset='utf-8'/>
            <style>
              :root {{ --w: 680px; }}
              body {{ margin:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; }}
              .card {{ width:var(--w); padding:16px 20px 20px; background:#fff; }}
              .header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 8px; background:#f5f8ff; border-radius:12px; color:#173172; font-weight:600; font-size:22px; }}
              .list {{ margin-top:8px; display:flex; flex-direction:column; gap:8px; }}
              .row {{ display:grid; grid-template-columns: 36px 56px 1fr 80px; align-items:center; gap:10px; padding:10px 10px; border-radius:12px; background:#fbfdff; border:1px solid #eef3ff; }}
              .rank {{ width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#000; font-weight:600; }}
              .avatar-wrap {{ position:relative; width:56px; height:56px; border-radius:50%; overflow:hidden; background:#eee; display:flex; align-items:center; justify-content:center; }}
              .avatar {{ width:100%; height:100%; object-fit:cover; display:block; }}
              .avatar-fallback {{ display:none; width:100%; height:100%; border-radius:50%; background:#789; color:#fff; font-weight:700; font-size:22px; align-items:center; justify-content:center; }}
              .avatar-wrap.fallback .avatar-fallback {{ display:flex; }}
              .user {{ display:flex; align-items:center; gap:8px; }}
              .username {{ color:#222; font-size:18px; font-weight:600; }}
              .pill {{ display:inline-block; max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding:6px 12px; border-radius:12px; border:2px solid; font-size:14px; font-weight:600; flex-shrink:0; }}
              .ac {{ color:#0a9c54; font-weight:800; font-size:22px; justify-self:end; }}
              .note {{ color:#6b7280; font-weight:500; font-size:12px; }}
            </style>
          </head>
          <body>
            <div class='card'>
              <div class='header'>
                <span>最近一周过题榜单</span>
                <span class='note'>图片来源于安心Bot</span>
              </div>
              <div class='list'>
                {''.join(rows)}
              </div>
            </div>
          </body>
        </html>
        """
        out_path = os.path.abspath("plugins/scpc/assets/scpc_week_rank.png")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 720, "height": 600})
            await page.set_content(html)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            card = page.locator(".card")
            try:
                await card.wait_for(state="visible")
            except Exception:
                pass
            try:
                h = await page.evaluate(
                    "document.querySelector('.card')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size({"width": 720, "height": int(h) + 40})
            except Exception:
                pass
            ok = False
            try:
                await card.screenshot(path=out_path)
                ok = os.path.exists(out_path)
            except Exception:
                ok = False
            if not ok:
                try:
                    await page.screenshot(path=out_path, full_page=False)
                    ok = os.path.exists(out_path)
                except Exception:
                    ok = False
            await browser.close()
        return out_path if ok else None
    except Exception:
        return None


async def render_scpc_user_info_image(
    nickname: str,
    signature: str,
    total: int,
    ac: int,
    accept_ratio: str,
    username: str,
    avatar: str,
) -> str | None:
    try:
        title = "SCPC 个人信息"
        html = f"""
        <html>
          <head>
            <meta charset='utf-8'/>
            <style>
              :root {{ --w: 680px; }}
              body {{ margin:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; }}
              .card {{ width:var(--w); padding:16px 20px 20px; background:#fff; }}
              .header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 8px; background:#f5f8ff; border-radius:12px; color:#173172; font-weight:600; font-size:22px; }}
              .note {{ color:#6b7280; font-weight:500; font-size:12px; }}
              .profile {{ display:grid; grid-template-columns: 72px 1fr; align-items:center; gap:14px; padding:14px 8px; }}
              .avatar-wrap {{ position:relative; width:72px; height:72px; border-radius:50%; overflow:hidden; background:#f3f4f6; display:flex; align-items:center; justify-content:center; border:2px solid #c7d2fe; box-shadow:0 2px 6px rgba(0,0,0,0.08); }}
              .avatar {{ width:100%; height:100%; object-fit:cover; display:block; }}
              .avatar-fallback {{ display:none; width:100%; height:100%; border-radius:50%; background:#64748b; color:#fff; font-weight:800; font-size:28px; align-items:center; justify-content:center; }}
              .avatar-wrap.fallback .avatar-fallback {{ display:flex; }}
              .nickname {{ color:#111827; font-size:22px; font-weight:800; }}
              .handle {{ color:#6b7280; font-size:14px; font-weight:600; margin-left:8px; }}
              .signature {{ color:#6b7280; font-size:14px; margin-top:4px; }}
              .stats {{ margin-top:10px; display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; }}
              .stat {{ background:#fbfdff; border:1px solid #eef3ff; border-radius:12px; padding:12px; display:flex; flex-direction:column; gap:6px; }}
              .stat-label {{ color:#6b7280; font-size:12px; }}
              .stat-value {{ color:#111827; font-size:20px; font-weight:800; }}
            </style>
          </head>
          <body>
            <div class='card'>
              <div class='header'>
                <span>{title}</span>
                <span class='note'>图片来源于安心Bot</span>
              </div>
              <div class='profile'>
                <div class='avatar-wrap'>
                  <img class='avatar' src='{avatar}' onerror="this.style.display='none'; this.parentNode.classList.add('fallback')"/>
                  <div class='avatar-fallback'>{(nickname[:1] or username[:1] or ' ').upper()}</div>
                </div>
                <div>
                  <div class='nickname'>{nickname}<span class='handle'>@{username}</span></div>
                  <div class='signature'>{signature}</div>
                </div>
              </div>
              <div class='stats'>
                <div class='stat'><div class='stat-label'>提交数</div><div class='stat-value'>{total}</div></div>
                <div class='stat'><div class='stat-label'>AC数</div><div class='stat-value'>{ac}</div></div>
                <div class='stat'><div class='stat-label'>通过率</div><div class='stat-value'>{accept_ratio}%</div></div>
              </div>
            </div>
          </body>
        </html>
        """
        out_path = os.path.abspath(f"plugins/scpc/assets/scpc_user_{username}.png")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 720, "height": 600})
            await page.set_content(html)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            card = page.locator(".card")
            try:
                await card.wait_for(state="visible")
            except Exception:
                pass
            try:
                h = await page.evaluate(
                    "document.querySelector('.card')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size({"width": 720, "height": int(h) + 40})
            except Exception:
                pass
            ok = False
            try:
                await card.screenshot(path=out_path)
                ok = os.path.exists(out_path)
            except Exception:
                ok = False
            if not ok:
                try:
                    await page.screenshot(path=out_path, full_page=False)
                    ok = os.path.exists(out_path)
                except Exception:
                    ok = False
            await browser.close()
        return out_path if ok else None
    except Exception:
        return None


async def render_scpc_contests_image(contests: List[Contest]) -> str | None:
    try:
        now_ts = int(__import__("datetime").datetime.now().timestamp())
        rows = []
        for c in contests:
            t = extract_contest_timing(c, now_ts)
            if not t:
                continue
            state, remaining_label, remaining_secs, duration_secs, start_ts, _ = t
            icon = state_icon(state)
            start_str = format_timestamp(start_ts)
            remaining_str = format_relative_hours(remaining_secs, precision=1)
            duration_str = format_hours(duration_secs, precision=1)
            cid = c.id
            id_pill = "" if not cid else f"<span class='pill'>ID {cid}</span>"
            rows.append(
                f"""
                <div class='row'>
                  <div class='title'>
                    <span class='state'>{icon} {state}</span>
                    <span class='name'>{c.name}</span>
                    {id_pill}
                  </div>
                  <div class='meta'>开始: {start_str} · {remaining_label}: {remaining_str} · 时长: {duration_str} 小时</div>
                </div>
                """
            )
        html = f"""
        <html>
          <head>
            <meta charset='utf-8'/>
            <style>
              :root {{ --w: 680px; }}
              body {{ margin:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; }}
              .card {{ width:var(--w); padding:16px 20px 20px; background:#fff; }}
              .header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 8px; background:#f5f8ff; border-radius:12px; color:#173172; font-weight:600; font-size:22px; }}
              .note {{ color:#6b7280; font-weight:500; font-size:12px; }}
              .list {{ margin-top:8px; display:flex; flex-direction:column; gap:8px; }}
              .row {{ display:flex; flex-direction:column; gap:6px; padding:10px 10px; border-radius:12px; background:#fbfdff; border:1px solid #eef3ff; }}
              .title {{ display:flex; align-items:center; gap:8px; }}
              .state {{ color:#0f172a; font-weight:700; }}
              .name {{ color:#111827; font-size:16px; font-weight:700; }}
              .pill {{ display:inline-block; padding:4px 10px; border-radius:12px; border:1px solid #c7d2fe; color:#3730a3; background:#eef2ff; font-size:12px; font-weight:600; }}
              .meta {{ color:#6b7280; font-size:13px; }}
            </style>
          </head>
          <body>
            <div class='card'>
              <div class='header'>
                <span>SCPC 比赛信息</span>
                <span class='note'>图片来源于安心Bot</span>
              </div>
              <div class='list'>
                {''.join(rows)}
              </div>
            </div>
          </body>
        </html>
        """
        out_path = os.path.abspath("plugins/scpc/assets/scpc_contests.png")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 720, "height": 600})
            await page.set_content(html)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            card = page.locator(".card")
            try:
                await card.wait_for(state="visible")
            except Exception:
                pass
            try:
                h = await page.evaluate(
                    "document.querySelector('.card')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size({"width": 720, "height": int(h) + 40})
            except Exception:
                pass
            ok = False
            try:
                await card.screenshot(path=out_path)
                ok = os.path.exists(out_path)
            except Exception:
                ok = False
            if not ok:
                try:
                    await page.screenshot(path=out_path, full_page=False)
                    ok = os.path.exists(out_path)
                except Exception:
                    ok = False
            await browser.close()
        return out_path if ok else None
    except Exception:
        return None


def generate_excel_contest_rank(rank_users: List[ScpcContestRankUser], contest_id: int):
    workbook = xlsxwriter.Workbook(f"SCPC_{contest_id}.xlsx")
    worksheet = workbook.add_worksheet()
    header_format = workbook.add_format(
        {
            "bold": True,
            "fg_color": "#D7E4BC",
            "border": 1,
            "align": "center",
            "font_size": 14,
        }
    )

    ac_format = workbook.add_format(
        {
            "fg_color": "#98FB98",
            "align": "center",
            "bold": True,
            "border": 1,
        }
    )
    first_ac_format = workbook.add_format(
        {
            "fg_color": "#4169E1",
            "font_size": 12,
            "align": "center",
            "bold": True,
            "border": 1,
        }
    )
    center_format = workbook.add_format({"align": "center"})

    field_names = [field.name for field in fields(rank_users[0])]
    field_names.pop()
    chinese_headers = rank_users[0].get_chinese_headers()
    chinese_field_names = [chinese_headers[field_name] for field_name in field_names]

    last_index = 0
    for col, chinese_name in enumerate(chinese_field_names):
        worksheet.write(0, col, chinese_name, header_format)
        last_index = col

    last_index += 1

    for problem, information in rank_users[0].information.items():
        worksheet.write(0, last_index, problem, header_format)
        last_index += 1

    for row, item in enumerate(rank_users, start=1):
        column = 0
        for col, field_name in enumerate(field_names):
            try:
                value = getattr(item, field_name)
                if isinstance(value, (int, float)):
                    worksheet.write_number(row, col, value, center_format)
                else:
                    worksheet.write_string(row, col, str(value), center_format)

            except Exception as e:
                print(f"错误处理行 {row} 列 {col} (字段: {field_name}): {e}")
                worksheet.write_string(row, col, "错误", center_format)

            column = col

        column += 1
        for problem, information in item.information.items():
            if information.is_ac:
                if information.is_first_ac:
                    worksheet.write_string(row, column, f"率先AC", first_ac_format)
                else:
                    worksheet.write_string(row, column, f"AC", ac_format)
            else:
                worksheet.write_string(row, column, "")
            column += 1

    # 调整列宽
    for col, chinese_name in enumerate(chinese_field_names):
        # 考虑中文字符宽度，适当增加列宽
        width = max(len(chinese_name) + 12, 12)
        worksheet.set_column(col, col, width)

    workbook.close()
    return os.path.abspath(f"SCPC_{contest_id}.xlsx")
