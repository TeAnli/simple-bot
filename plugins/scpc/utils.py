from datetime import datetime
from typing import Optional, Dict, Any
from ncatbot.utils import get_log
from dataclasses import dataclass

import math
import requests

LOG = get_log()

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
}


@dataclass
class Contest:
    name: str  # 比赛名称
    start_ts: int  # 开始时间戳（秒）
    url: str | None  # 比赛链接
    duration_secs: int  # 持续时间（秒）
    contest_id: int | None  # 比赛ID


def fetch_json(url: str, headers: dict = headers) -> Optional[Dict[str, Any]]:
    """
    使用统一请求头发起 GET 请求并解析 JSON 响应

    Args:
    - url: 请求地址

    Returns:
    - 解析后的 JSON 字典; 失败返回 None
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        LOG.warning(f"HTTP 请求失败: {e}")
        return None
    if response.status_code != 200:
        LOG.warning(
            f"请求 {url} 返回状态码异常: {response.status_code} {response.text}"
        )
        return None
    try:
        return response.json()
    except Exception as e:
        LOG.warning(f"JSON 解析失败: {e}")
        return None


def format_timestamp(timestamp: int, format: str = "%Y-%m-%d %H:%M") -> str:
    """
    将时间戳格式化为指定的日期时间字符串

    Args:
    - timestamp: 时间戳（秒）
    - format: 时间格式字符串

    Returns:
    - 格式化后的时间字符串
    """
    return datetime.fromtimestamp(timestamp).strftime(format)


def format_hours(seconds: int, precision: int = 1) -> str:
    """
    将秒数转换为小时数，保留指定小数位

    Args:
    - seconds: 秒数
    - precision: 小数位数

    Returns:
    - 小时数字符串
    """
    hours = seconds / 3600
    return f"{hours:.{precision}f}"


def format_relative_hours(seconds: int, precision: int = 1) -> str:
    """
    将秒数格式化为相对时间描述：小时/天/周

    规则:
    - < 1 天：返回小时数
    - < 7 天：返回天数
    - 其他：返回周数

    参数:
    - seconds: 秒数
    - precision: 小数位数（用于小时）

    返回:
    - 相对时间字符串
    """
    hours = seconds / 3600
    if hours >= 24 * 7:
        weeks = math.ceil(hours / (24 * 7))
        return f"{weeks} 周"
    if hours >= 24:
        days = math.ceil(hours / 24)
        return f"{days} 天"
    return f"{hours:.{precision}f} 小时"


def state_icon(state: str) -> str:
    """
    根据比赛状态返回对应图标

    Args:
    - state: 比赛状态（即将开始/进行中/已结束）

    Returns:
    - 对应状态的图标字符串
    """
    mapping = {
        "即将开始": "⏳",
        "进行中": "🟢",
        "已结束": "🔴",
    }
    return mapping.get(state, "ℹ️")


def format_contest_text(
    name: str,
    contest_id: int | None,
    state: str,
    start_ts: int,
    remaining_label: str,
    remaining_secs: int,
    duration_secs: int,
    include_id: bool = True,
    contest_url: str | None = None,
) -> str:
    """
    概述:
    统一格式化各平台的比赛信息为展示文本

    参数:
    - name: 比赛名称
    - contest_id: 比赛 ID（可为 None）
    - state: 比赛状态（即将开始/进行中/已结束）
    - start_ts: 开始时间戳（秒）
    - remaining_label: 剩余时间标签文案
    - remaining_secs: 剩余时间（秒）
    - duration_secs: 比赛持续时间（秒）
    - include_id: 是否在标题行中包含比赛 ID
    - contest_url: 比赛链接（可选）

    返回:
    - 格式化后的比赛信息多行文本
    """
    icon = state_icon(state)
    start_time_str = format_timestamp(start_ts)
    duration_hours = format_hours(duration_secs, precision=1)
    remaining_str = format_relative_hours(remaining_secs, precision=1)

    title_line = (
        f"{name}"
        if not include_id or contest_id is None
        else f"{name} (ID: {contest_id})"
    )
    lines = [
        "比赛名称:",
        f"{title_line}",
        f"状态: {icon} {state}",
        f"开始时间: {start_time_str}",
        f"{remaining_label}: {remaining_str}",
        f"比赛时长: {duration_hours} 小时",
    ]
    if contest_url:
        lines.append(f"比赛地址: {contest_url}")
    return "\n".join(lines)


def parse_scpc_time(value) -> int:
    """
    解析来自后端GMT未经格式化的时间字段为时间戳

    Args:
    - value: 原始时间值（可能是秒 数字ISO 字符串等）

    Returns:
    - 解析得到的时间戳（秒）无法解析返回 0
    """
    if value is None:
        return 0
    try:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
                return int(dt.timestamp())
            except Exception:
                pass
            try:
                v = value.replace("Z", "+00:00")
                dt = datetime.fromisoformat(v)
                return int(dt.timestamp())
            except Exception:
                pass
    except Exception:
        pass
    return 0


def calculate_accept_ratio(total_count: int, accept_count: int) -> float:
    """
    计算比率

    Args:
    - total_count: 总提交数
    - accept_count: 通过数

    Returns:
    - 通过率（浮点数）当 `total_count` 为 0 返回 0.0
    """
    if total_count == 0:
        return 0.0
    return accept_count / total_count


async def broadcast_text(api_client, group_listeners: dict, text: str):
    """
    向已开启监听的群聊广播文本消息

    Args:
    - api_client: 机器人 API 客户端
    - group_listeners: 群组监听开关映射（group_id -> enabled）
    - text: 要广播的文本内容
    """
    for gid, enabled in group_listeners.items():
        if enabled:
            await api_client.send_group_text(gid, text)


def extract_contest_timing(contest: Contest, now_ts: int):
    """
    根据统一 Contest 对象计算比赛状态与剩余时间。

    Args:
    - contest: 统一比赛对象。
    - now_ts: 当前时间戳（秒）。

    Returns:
    - (state, remaining_label, remaining_secs, duration_secs, start_ts, sort_key)
    - 比赛已结束返回 None。
    """
    start_ts = int(contest.start_ts or 0)
    duration = int(contest.duration_secs or 0)
    if start_ts <= 0 or duration <= 0:
        return None
    end_ts = start_ts + duration
    if now_ts < start_ts:
        remaining = start_ts - now_ts
        return (
            "即将开始",
            "据开始还剩",
            remaining,
            duration,
            start_ts,
            remaining,
        )
    if start_ts <= now_ts < end_ts:
        remaining = end_ts - now_ts
        return (
            "进行中",
            "距离结束",
            remaining,
            duration,
            start_ts,
            remaining,
        )
    return None
