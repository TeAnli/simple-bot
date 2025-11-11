# 通用headers
import requests
from typing import Optional, List, Dict, Any
from ncatbot.utils import get_log

_logger = get_log()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'Content-Type': 'application/json',
}
# 获取 scpc 用户信息
def user_info_url(username: str) -> str:
    return f'http://scpc.fun/api/get-user-home-info?username={username}'
# 获取 codeforces 比赛信息
def codeforces_contests_url(include_gym: bool = False) -> str:
    return f'https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}'
# 获取 洛谷 比赛信息
def luogu_contests_url(page: int = 1) -> str:
    return f'https://www.luogu.com.cn/contest/list?_contentOnly=1&page={page}'
# 获取 scpc 比赛信息
def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    return f'http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}'
# 获取 codeforces 用户积分
def codeforces_user_rating_url(username: str) -> str:
    return f'https://codeforces.com/api/user.rating?handle={username}'

def fetch_json(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """统一的 HTTP JSON 获取函数。"""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except Exception as e:
        _logger.warning(f'HTTP request failed: {e}')
        return None
    if getattr(resp, 'status_code', 0) != 200:
        _logger.warning(f'Bad status fetching {url}: {getattr(resp, "status_code", "")} {getattr(resp, "text", "")}')
        return None
    try:
        return resp.json()
    except Exception as e:
        _logger.warning(f'JSON decode failed: {e}')
        return None

def get_codeforces_contests(include_gym: bool = False, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """获取 Codeforces 比赛列表"""
    body = fetch_json(codeforces_contests_url(include_gym), timeout=timeout)
    if not body or body.get('status') != 'OK':
        _logger.warning(f'Codeforces API not OK or empty: {body}')
        return None
    return body.get('result', [])

def get_codeforces_user_rating(handle: str, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """获取 Codeforces 用户积分变更记录"""
    body = fetch_json(codeforces_user_rating_url(handle), timeout=timeout)
    if not body or body.get('status') != 'OK':
        _logger.warning(f'Codeforces rating API not OK or empty: {body}')
        return None
    return body.get('result', [])

def get_scpc_user_info(username: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """获取 SCPC 用户信息"""
    body = fetch_json(user_info_url(username), timeout=timeout)
    if not body or 'data' not in body:
        _logger.warning(f'SCPC user info API empty or bad: {body}')
        return None
    return body.get('data')

def get_scpc_contests(current_page: int = 0, limit: int = 10, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """获取 SCPC 比赛列表"""
    body = fetch_json(scpc_contests_url(current_page, limit), timeout=timeout)
    if not body:
        _logger.warning('SCPC contests API returned empty body')
        return None
    records = (
        body.get('data', {}).get('records')
        or body.get('records')
        or []
    )
    return records

