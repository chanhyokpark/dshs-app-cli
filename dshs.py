#!/usr/bin/env python3
"""
DSHS.PY
dshs.app을 cli에서 접근할 수 있도록 하는 Python 코드
작동하면 된다는 마인드로 최대한 대충 짬
버전 0.0.1
(c) 박찬혁
"""
import argparse
import json
import webbrowser
import logging
from datetime import datetime, timedelta
import re

try:
    import requests
except ImportError:
    print("requests가 설치되어 있지 않습니다. 다음 명령어 실행:\npip install requests")
    exit(1)

try:
    import tabulate
except ImportError:
    print("tabulate가 설치되어 있지 않습니다. 다음 명령어 실행:\npip install tabulate")
    exit(1)

import os
import sys


grey = "\x1b[38;21m"
yellow = "\x1b[33;21m"
# red = "\x1b[31;21m"
bold = "\033[1m"
red = "\033[91m"
bold_red = "\x1b[31;1m"
green = "\033[92m"
reset = "\x1b[0m"


class CustomFormatter(logging.Formatter):
    """logger Formatter to add colors and count warning / errors"""

    format = "%(message)s"
    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + "경고: " + format + reset,
        logging.ERROR: bold + red + "오류: " + format + reset,
        logging.CRITICAL: bold_red + "치명적 오류: " + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger("dshs.py")
logger.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch.setFormatter(CustomFormatter())

logger.addHandler(ch)


is_interactive = os.isatty(sys.stdout.fileno())
config_path = os.path.join(os.path.expanduser("~"), ".dshsconfig.json")
version = "0.0.1"


class Config:
    def __init__(self):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get(self, field):
        if field not in self.config:
            return None
        return self.config[field]

    def set(self, field, value):
        self.config[field] = value

    def save(self):
        with open(config_path, "w+", encoding="utf-8") as f:
            json.dump(self.config, f)


config = Config()


base_address = "https://www.dshs.app/"
api_address = base_address + "api/v1/"
auth_address = base_address + "authorize"
client_id = "sss"
client_secret = "ddd"


class Requester:
    def __init__(self, token):
        self.token = token
        self.header = {"Authorization": f"Bearer {token}"}

    def get(self, endpoint: str, params=None):
        result = requests.get(
            api_address + endpoint, params=params, headers=self.header
        )
        result.raise_for_status()
        return result.json()

    def post(self, path: str, params: dict):
        result = requests.post(api_address + path, data=params, headers=self.header)
        result.raise_for_status()
        return result.json()

    def put(self, path: str, params: dict):
        result = requests.put(api_address + path, data=params, headers=self.header)
        result.raise_for_status()
        return result.json()

    def delete(self, path: str, params: dict):
        result = requests.delete(api_address + path, data=params, headers=self.header)
        result.raise_for_status()
        return result.json()


def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 401:
                    logger.error("로그인하지 않았거나 토큰이 만료되었습니다. 다음 명령어 실행:\ndshs auth")
                elif e.response.status_code == 500:
                    logger.error("서버 오류가 발생했습니다.")
                elif e.response.status_code == 400:
                    logger.error("올바르지 않은 요청")
                elif e.response.status_code == 403:
                    logger.error("권한이 없습니다.")
            raise e
        except requests.exceptions.ConnectionError as e:
            logger.error("오류: 서버와 연결하지 못했습니다.")
            raise e

    return wrapper


class Auth:
    def __init__(self):
        self.access_token = config.get("access-token") or ""

    def get_access_token(self, code):
        res = requests.post(
            api_address + "token",
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        res.raise_for_status()
        self.access_token = res.json()["access_token"]
        config.set("access-token", self.access_token)


class Client:
    def __init__(self):
        self.auth = Auth()
        self.requester = Requester(self.auth.access_token)

    @error_handler
    def meal(self, date: str):
        try:
            res = self.requester.get(f"meals/{date}")
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            else:
                raise e

    def check_update(self):
        res = self.requester.get("check-cli-update", {"current-version": version})
        return res
        # return {"update": False}

    @error_handler
    def userinfo(self):
        res = self.requester.get("userinfo")
        return res

    @error_handler
    def penalty(self, f=None, t=None):
        d = {}
        if f:
            d["from"] = f
        if t:
            d["to"] = t
        res = self.requester.get("penalties", d)
        return res

    @error_handler
    def get_outrequests(self, f=None, t=None):
        d = {}
        if f:
            d["from"] = f
        if t:
            d["to"] = t
        try:
            res = self.requester.get("outrequests", d)
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            else:
                raise e

    @error_handler
    def create_outrequest(
        self, from_date: datetime, to_date: datetime, category=None, reason=None
    ):
        formatted_from_date = from_date.strftime("%Y-%m-%dT%H:%M")
        formatted_to_date = to_date.strftime("%Y-%m-%dT%H:%M")

        data = {"from": formatted_from_date, "to": formatted_to_date}
        if category is not None:
            data["category"] = category
        if reason:
            data["reason"] = reason

        try:
            res = self.requester.post("outrequests", params=data)
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                return {"error": "invalid format"}
            else:
                raise e

    @error_handler
    def get_code(self, code=None, browser=True):
        c = code
        url = f"{auth_address}?client_id={client_id}&redirect_uri={base_address}code"
        if not c and is_interactive:
            if browser:
                print("코드를 붙여넣으세요: ", end="")
                webbrowser.open(url)
            else:
                print(f"{url} 에 접속한 뒤 코드를 붙여넣으세요: ", end="")
            c = input()
        else:
            if c is None:
                print(f"{url} 에 접속한 뒤 다음 명령어를 실행하세요:\ndshs auth --code {{코드}}")
        try:
            self.auth.get_access_token(c)
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 400:
                    logger.error("로그인에 실패했습니다. 코드가 틀렸습니다.")
            raise Exception
        logger.info("로그인 성공")

    @error_handler
    def get_space_room(self, room):
        try:
            res = self.requester.get(f"spaces/rooms/{room}")
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.error(f"'{room}': 존재하지 않는 자습실입니다.")
                raise Exception
            else:
                raise e

    @error_handler
    def get_space_area(self, area):
        try:
            res = self.requester.get(f"spaces/areas/{area}")
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.error(f"'{area}': 존재하지 않는 구역입니다.")
                raise Exception
            else:
                raise e

    @error_handler
    def get_area(self, date: datetime, area):
        try:
            res = self.requester.get(
                f"reservations/{date.strftime('%Y%m%d')}/areas/{area}"
            )
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.error(f"'{area}': 존재하지 않는 구역입니다.")
                raise Exception
            else:
                raise e

    @error_handler
    def get_room(self, date: datetime, room):
        try:
            res = self.requester.get(
                f"reservations/{date.strftime('%Y%m%d')}/rooms/{room}"
            )
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.error(f"'{room}': 존재하지 않는 자습실입니다.")
                raise Exception
            else:
                raise e

    @error_handler
    def search(self, date: datetime, query):
        try:
            res = self.requester.get(
                f"reservations/{date.strftime('%Y%m%d')}/search", {"q": query}
            )
            if res is None:
                logger.error("해당 학생이 신청하지 않았습니다.")
                raise Exception
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    logger.error(f"'{query}': 존재하지 않는 학생입니다.")
                    raise Exception
                elif e.response.status_code == 422:
                    logger.error(f"'{query}': 동명이인이 존재합니다. '{query}1'과 같은 형식을 사용하세요")
                    raise Exception
            else:
                raise e

    @error_handler
    def search_me(self, date: datetime):
        res = self.requester.get(f"reservations/{date.strftime('%Y%m%d')}")
        if res is None:
            logger.error("신청하지 않았습니다.")
            raise Exception
        return res

    @error_handler
    def reserve(self, date: datetime, seat):
        room = seat[0]
        area = seat[:2]
        try:
            res = self.requester.post(
                f"reservations/{date.strftime('%Y%m%d')}",
                {"room_name": room, "area_name": area, "seat_name": seat},
            )
            return res
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    logger.error(f"'{seat}': 존재하지 않는 좌석입니다.")
                    raise Exception
                elif e.response.status_code == 406:
                    logger.error(f"신청 실패. 사유: {e.response.json()['error']}")
                    raise Exception
                else:
                    raise e


parser = argparse.ArgumentParser(description="dshs.app CLI")
# parser.register("action", "parsers", AliasedSubParsersAction)
subparsers = parser.add_subparsers(dest="command")
subparsers.required = True
auth_parser = subparsers.add_parser("auth", aliases=["a"])
auth_parser.add_argument("-c", "--code", dest="code", required=False)
update_parser = subparsers.add_parser("update")
userinfo_parser = subparsers.add_parser("userinfo")
userinfo_parser.add_argument(
    "field", nargs="?", help="name, student_id 등 필드, 비어 있으면 전체 json 출력"
)
penalty_parser = subparsers.add_parser("penalty", aliases=["p"])
penalty_parser.add_argument(
    "-p", "--point", dest="only_points", action="store_true", help="기록을 보여주지 않고 점수만 확인"
)
penalty_parser.add_argument(
    "-a",
    "--all",
    dest="recent",
    action="store_true",
    default=False,
    help="전체 벌점 내역 확인(기본값: 7일 전~오늘)",
)

meal_parser = subparsers.add_parser("meal")
meal_parser.add_argument(
    "date",
    nargs="?",
    default=datetime.now().strftime("%Y%m%d"),
    help="yyyymmdd 또는 mmdd 포맷의 날짜, 기본값은 오늘",
)

reserve_parser = subparsers.add_parser("reserve", help="자습 신청", aliases=["r"])
reserve_parser.add_argument(
    "-d",
    "--date",
    dest="date",
    default="today",
    help="날짜 (YYYYMMDD 또는 today/tomorrow, 기본값은 today)",
)
reserve_parser.add_argument(
    "-c",
    "--create",
    dest="create",
    action="store_true",
    default=False,
    help="해당 장소에 신청(좌석을 검색했을 때만 가능)",
)
reserve_parser.add_argument(
    "query", nargs="?", help="검색어(자습실, 구역, 좌석, 사용자 이름 또는 별칭, 사용자 학번, me는 자신의 학습 장소)"
)
reserve_parser.add_argument(
    "-u",
    "--update",
    dest="update",
    action="store_true",
    default=False,
    help="좌석 정보 강제 업데이트",
)

args = parser.parse_args()
api = Client()
if not config.get("update-checked"):
    config.set("update-checked", "19721121")
if (
    datetime.now() - datetime.strptime(config.get("update-checked"), "%Y%m%d")
).days > 3:
    try:
        res = api.check_update()
        if res["update"]:
            print(f'새 버전: {res["version"]}')
            print(f'다운로드 링크: {res["download_link"]}')
        else:
            config.set("update-checked", datetime.now().strftime("%Y%m%d"))
    except Exception:
        pass
try:
    if args.command in ["auth", "a"]:
        if args.code:
            api.get_code(code=args.code)
        else:
            api.get_code()
    elif args.command in ["userinfo"]:
        res = api.userinfo()
        if args.field:
            if args.field in res.keys():
                print(res[args.field])
            else:
                logger.error("존재하지 않는 필드")
        else:
            print(json.dumps(res, indent=4, ensure_ascii=False))
    elif args.command in ["penalty", "p"]:
        res = None
        if not args.recent:
            res = api.penalty((datetime.now() - timedelta(days=7)).strftime("%Y%m%d"))
        else:
            res = api.penalty()
        print(
            f"전체 벌점: {bold}{green if res['total']<0 else (red if res['total']>=30 else (yellow if res['total']>=20 else ''))}{res['total']}점"
        )
        print(reset, end="")
        if not args.only_points:
            print("벌점 내역:\n")
            for d in res["data"]:
                try:
                    print(
                        f'일자: {(datetime.fromisoformat(d["date"].replace("Z", "+00:00"))+timedelta(hours=9)).strftime("%Y.%m.%d")}'
                    )
                    print(
                        f'점수: {(red+"+") if d["points"]>0 else green}{d["points"]}점{reset}'
                    )
                    print(f"사유: {d['reason']}")
                    print(f"부과 교사: {d['giver']['name']}")
                    print("____________")
                    print()
                except Exception:
                    pass
    elif args.command in ["meal"]:
        d = None
        if len(args.date) == 4:
            d = datetime.now().year + args.date
        else:
            d = args.date
        data = api.meal(d)
        if not data:
            print("급식 없음")
        else:
            print(
                bold
                + datetime.strptime(d, "%Y%m%d").strftime("%Y년 %m월 %d일")
                + "의 급식\n"
                + reset
            )
            mn = ["아침", "점심", "저녁"]
            for i in range(3):
                print(bold + mn[i] + reset)
                print(data[i])
                print()
    elif args.command in "update":
        res = api.check_update()
        if res["update"]:
            print(f'새 버전: {res["version"]}')
            print(f'다운로드 링크: {res["download_link"]}')
        else:
            print("최신 버전입니다.")
            config.set("update-checked", datetime.now().strftime("%Y%m%d"))
    elif args.command in ["reserve", "r"]:
        query = args.q
        input_date = args.date
        date = datetime.now()
        if input_date == "today":
            date = datetime.now()
        if input_date == "tomorrow":
            date = datetime.now() - timedelta(days=1)
        else:
            date = datetime.strptime(input_date, "%Y%m%d")
        if re.match(r"^[abs]$", query):
            pass
        elif re.match(r"^[abs]\d$", query):
            pass
        elif re.match(r"^[abs]\d{3}$", query):
            pass
        elif re.match(r"^([가-힣]{2,5})|([1-3]\d{3})$", query):
            pass
        elif query == "me":
            pass
        else:
            logger.error(f"'{query}': 올바르지 않은 검색어입니다.")
        raise NotImplementedError

    config.save()
except Exception as e:
    print(e)
    logger.info("명령 실행 실패.")
    exit(1)
