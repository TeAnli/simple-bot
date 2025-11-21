from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .utils import fetch_json

def codeforces_contests_url(include_gym: bool = False) -> str:
    return f'https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}'

def codeforces_user_rating_url(username: str) -> str:
    return f'https://codeforces.com/api/user.rating?handle={username}'

@dataclass
class CodeforcesContest:
    id: int
    name: str
    durationSeconds: int
    startTimeSeconds: int
    relativeTimeSeconds: int

@dataclass
class CodeforcesUserRatingChange:
    contestId: int
    contestName: str
    handle: str
    newRating: int
    oldRating: int
    ratingUpdateTimeSeconds: int

def extract_cf_timing(contest: CodeforcesContest):
    relative_secs = int(contest.relativeTimeSeconds or 0)
    duration_secs = int(contest.durationSeconds or 0)
    start_ts = int(contest.startTimeSeconds or 0)
    if relative_secs < 0:
        return '即将开始', '据开始还剩', abs(relative_secs), duration_secs, start_ts
    if 0 <= relative_secs < duration_secs:
        return '进行中', '距离结束', max(duration_secs - relative_secs, 0), duration_secs, start_ts
    return None


def get_codeforces_contests(include_gym: bool = False, timeout: int = 10) -> Optional[List[CodeforcesContest]]:
    json_data = fetch_json(codeforces_contests_url(include_gym), timeout=timeout)
    if not json_data or json_data.get('status') != 'OK':
        return None
    records = json_data.get('result', [])
    contests: List[CodeforcesContest] = []
    for entry in records:
        try:
            contests.append(CodeforcesContest(
                id=int(entry.get('id', 0)),
                name=str(entry.get('name', '')),
                durationSeconds=int(entry.get('durationSeconds', 0)),
                startTimeSeconds=int(entry.get('startTimeSeconds', 0)),
                relativeTimeSeconds=int(entry.get('relativeTimeSeconds', 0)),
            ))
        except Exception:
            continue
    return contests

def get_codeforces_user_rating(handle: str, timeout: int = 10) -> Optional[List[CodeforcesUserRatingChange]]:
    json_data = fetch_json(codeforces_user_rating_url(handle), timeout=timeout)
    if not json_data or json_data.get('status') != 'OK':
        return None
    records = json_data.get('result', [])
    changes: List[CodeforcesUserRatingChange] = []
    for entry in records:
        try:
            changes.append(CodeforcesUserRatingChange(
                contestId=int(entry.get('contestId', 0)),
                contestName=str(entry.get('contestName', '')),
                handle=str(entry.get('handle', handle)),
                newRating=int(entry.get('newRating', 0)),
                oldRating=int(entry.get('oldRating', 0)),
                ratingUpdateTimeSeconds=int(entry.get('ratingUpdateTimeSeconds', 0)),
            ))
        except Exception:
            continue
    return changes