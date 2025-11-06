
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'Content-Type': 'application/json',
    'Host': 'scpc.fun'
}

def user_info_url(username: str) -> str:
    return f'http://scpc.fun/api/get-user-home-info?username={username}'

