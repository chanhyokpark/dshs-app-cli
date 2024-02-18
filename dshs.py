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
from itertools import cycle
from time import sleep
from threading import Thread
import re

try:
    import requests
except ImportError:
    print("requests가 설치되어 있지 않습니다. 다음 명령어 실행:\npip install requests")
    exit(1)

try:
    from tabulate import tabulate
except ImportError:
    print("tabulate가 설치되어 있지 않습니다. 다음 명령어 실행:\npip install tabulate")
    exit(1)

import os
import sys

version = "0.0.1"

grey = "\x1b[38;21m"
yellow = "\x1b[33m"
blue = "\033[96m"
# red = "\x1b[31;21m"
bold = "\033[1m"
red = "\033[91m"
bold_red = "\x1b[31;1m"
green = "\033[92m"
reset = "\x1b[0m"
bg_blue = "\x1b[44m"
underline = "\033[4m"


class CustomFormatter(logging.Formatter):
    """logger Formatter to add colors and count warning / errors"""

    format = "%(message)s"
    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: bold + yellow + "경고: " + format + reset,
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


class Loader:
    # https://stackoverflow.com/questions/22029562/python-how-to-make-simple-animated-loading-while-process-is-running
    def __init__(self, desc="Loading...", end="", timeout=0.1):
        """
        A loader-like context manager

        Args:
            desc (str, optional): The loader's description. Defaults to "Loading...".
            end (str, optional): Final print. Defaults to "Done!".
            timeout (float, optional): Sleep time between prints. Defaults to 0.1.
        """
        self.desc = desc
        self.end = end
        self.timeout = timeout

        self._thread = Thread(target=self._animate, daemon=True)
        self.steps = ["／", "－", "＼", "｜"]
        self.done = False

    def start(self):
        self._thread.start()
        return self

    def _animate(self):
        for c in cycle(self.steps):
            if self.done:
                break
            print(f"\r{self.desc} {c}", flush=True, end="")
            sleep(self.timeout)

    def __enter__(self):
        self.start()

    def stop(self):
        self.done = True
        cols = os.get_terminal_size().columns
        print("\r" + " " * cols, end="", flush=True)
        print(f"\r{self.end}", flush=True, end="\n" if len(self.end) else "")

    def __exit__(self, exc_type, exc_value, tb):
        # handle exceptions with those variables ^
        self.stop()


is_interactive = os.isatty(sys.stdout.fileno())
config_path = os.path.join(os.path.expanduser("~"), ".dshsconfig.json")


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
client_id = config.get("client_id") or "sss"
client_secret = config.get("client_secret") or "ddd"


def use_loader(func):
    def wrapper(*args, **kwargs):
        with Loader(bold + func.__name__.upper() + " " + args[1] + reset):
            res = func(*args, **kwargs)
            return res

    return wrapper


class Requester:
    def __init__(self, token):
        self.token = token
        self.header = {"Authorization": f"Bearer {token}"}

    @use_loader
    def get(self, path: str, params=None):
        result = requests.get(api_address + path, params=params, headers=self.header)
        result.raise_for_status()
        return result.json()

    @use_loader
    def post(self, path: str, params: dict):
        result = requests.post(api_address + path, data=params, headers=self.header)
        result.raise_for_status()
        return result.json()

    @use_loader
    def put(self, path: str, params: dict):
        result = requests.put(api_address + path, data=params, headers=self.header)
        result.raise_for_status()
        return result.json()

    @use_loader
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
        config.set(
            "student-id", Requester(self.access_token).get("userinfo")["student_id"]
        )


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
subparsers.required = False
auth_parser = subparsers.add_parser("auth", aliases=["a"])
auth_parser.add_argument("-c", "--code", dest="code", required=False)
auth_parser.add_argument(
    "-l",
    "--link",
    dest="link",
    required=False,
    default=False,
    action="store_true",
    help="웹페이지를 열지 않고 링크만 제공",
)
update_parser = subparsers.add_parser("update", help="이 앱 업데이트")
userinfo_parser = subparsers.add_parser("userinfo", help="사용자 정보")
userinfo_parser.add_argument(
    "field", nargs="?", help="name, student_id 등 필드, 비어 있으면 전체 json 출력"
)
penalty_parser = subparsers.add_parser("penalty", aliases=["p"], help="벌점 확인")
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

meal_parser = subparsers.add_parser("meal", help="급식 조회")
meal_parser.add_argument(
    "date",
    nargs="?",
    default=datetime.now().strftime("%Y%m%d"),
    help="yyyymmdd 또는 mmdd 포맷의 날짜, 기본값은 오늘",
)

reserve_parser = subparsers.add_parser("reserve", help="자습 신청", aliases=["r", "rt"])
reserve_parser.add_argument(
    "-d",
    "--date",
    dest="date",
    default="today",
    help="날짜 (YYYYMMDD 또는 today/tomorrow, 기본값은 today, 'rt' 명령어를 사용하면 tomorrow로 고정 )",
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
    "q",
    nargs="?",
    help="검색어(자습실, 구역, 좌석, 사용자 이름 또는 별칭, 사용자 학번, me는 자신의 학습 장소, 자습실을 검색했을 때 터미널이 iterm이거나 wezterm이고, 패키지 imgcat와 PIL을 설치하면 자습실 이미지가 제공됨니다)",
)
args = parser.parse_args()
api = Client()


def print_table(data, vertical=False):  # 3d 배열
    str_tables = []
    res = ""
    for t in data:
        str_tables.append(
            tabulate(t, headers=[], tablefmt="fancy_grid", stralign="center")
        )
    if vertical:
        res = ("\n" * 2).join(str_tables)
    else:
        max_r = max((len(d.split("\n")) for d in str_tables))
        c = tuple(len(d.split("\n")[0]) for d in str_tables)
        s = "\n" * max_r
        for i, t in enumerate(str_tables):
            sp = t.split("\n")
            for j in range(max_r):
                if len(sp) > j:
                    s = s.replace("\n", sp[j] + " " * 3 + "*", 1)
                else:
                    s = s.replace("\n", " " * (c[i] + 3) + "*", 1)
            s = s.replace("*", "\n")
        res = s
    width = len(res.split("\n")[0])
    if width > os.get_terminal_size().columns:
        logger.warning("터미널 크기가 너무 작습니다. 크기 변경을 시도합니다.")
        sys.stdout.write(
            "\x1b[8;{rows};{cols}t".format(
                rows=os.get_terminal_size().lines, cols=width + 1
            )
        )
    print(res)


def transform_table(r, c, seats, reserve_dict, highlight_seat, student_id, disabled):
    result = [[] for i in range(r)]
    keys = reserve_dict.keys()
    for i in range(r):
        for j in range(c):
            seat = seats[i * c + j]
            if seat in keys:
                d = reserve_dict[seat]
                seat = (
                    ((bold + bg_blue) if highlight_seat == seat else "")
                    + (red if d["student_id"] == student_id else grey)
                    + (seat if seat != "0" else "")
                    + reset
                )
                name = d["name"]
                if "alias" in d.keys() and d["alias"] is not None:
                    name = d["alias"]
                seat += f"\n{name}"
            else:
                seat = (
                    ((bold + bg_blue) if highlight_seat == seat else "")
                    + (grey if disabled else green)
                    + (seat if seat != "0" else "")
                    + reset
                )
                seat += "\n-"
            result[i].append(seat)
    return result


def transform_reserve(reserve_data):
    reserve_dict = {}
    if not reserve_data:
        return {}
    for d in reserve_data["seats"]:
        reserve_dict[d["seat_name"]] = d["user"]
    return reserve_dict


def process_table(
    area_seats_data, area_reserve_data, highlight_seat, student_id, disabled
):
    table_data = []
    reserve_dict = transform_reserve(area_reserve_data)
    for t in area_seats_data["tables"]:
        table_data.append(
            transform_table(
                t["r"],
                t["c"],
                t["data"],
                reserve_dict,
                highlight_seat,
                student_id,
                disabled,
            )
        )
    print_table(table_data, area_seats_data["vertical"])


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

repeat = not args.command
if repeat:
    if not is_interactive:
        logger.warning("인터렉티브 터미널이 아닙니다.")
    logger.info("CTRL+C로 종료")
while True:
    try:
        if repeat:
            args = parser.parse_args(input(bold + green + "> " + reset).split())
        if args.command in ["auth", "a"]:
            if args.code:
                api.get_code(code=args.code)
            else:
                api.get_code(browser=not args.link)
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
                res = api.penalty(
                    (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                )
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
        elif args.command == "update":
            res = api.check_update()
            if res["update"]:
                print(f'새 버전: {res["version"]}')
                print(f'다운로드 링크: {res["download_link"]}')
            else:
                print("최신 버전입니다.")
                config.set("update-checked", datetime.now().strftime("%Y%m%d"))
        elif args.command in ["reserve", "r", "rt"]:
            query = args.q
            input_date = "tomorrow" if args.command == "rt" else args.date
            date = datetime.now()
            if input_date == "today":
                date = datetime.now()
            elif input_date == "tomorrow":
                date = datetime.now() + timedelta(days=1)
            else:
                date = datetime.strptime(input_date, "%Y%m%d")
            if re.match(r"^[abs]$", query):
                room_info = api.get_space_room(query)
                room_reserve_info = api.get_room(date, query)
                print(f"{bold}{query}({room_info['description']}){reset}")
                if query in ["a", "b"]:
                    try:
                        from imgcat import imgcat
                        from PIL import Image

                        img = None
                        with Loader("이미지 다운로드 중...") as loader:
                            img = Image.open(
                                requests.get(
                                    base_address + query + "_labeled.png", stream=True
                                ).raw
                            )
                        imgcat(img)
                    except Exception:
                        pass
                for i in range(len(room_info["areas"])):
                    print(f"{room_info['areas'][i]['area_name']}: ", end="")
                    seat_count = room_info["areas"][i]["count"]
                    seat_occupied = room_reserve_info["areas"][i]["occupied"]
                    print(
                        f"{bold}{yellow if seat_count>seat_occupied else red}{seat_occupied}{reset}/{bold}{seat_count}{reset}"
                    )
            else:
                if query == "me" or re.match(
                    r"^(([가-힣]{2,5}(\d?))|([1-3]\d{3}))$", query
                ):
                    res = {}
                    if query == "me":
                        res = api.search_me(date)
                    else:
                        res = api.search(date, query)
                    if not res:
                        print("오류")
                        query = ""
                    else:
                        print(
                            f"{bold}{res['user']['student_id']} {res['user']['name']}",
                            end="",
                        )
                        if "alias" in res["user"].keys():
                            print(f"('{res['user']['alias']}')", end="")
                        print(reset)
                        print(
                            f"신청 좌석: {bold}{res['seat_name'] if res['seat_name'] else '없음'}{reset}"
                        )
                        query = res["seat_name"] or ""
                if re.match(r"^[abs](\d|\d{3})$", query):
                    highlight_seat = ""
                    if len(query) == 4:
                        if args.create:
                            try:
                                res = api.reserve(date, query)
                                print(bold + green + f"좌석 {query}에 신청했습니다." + reset)
                            except Exception:
                                pass
                        highlight_seat = query
                        query = query[:2]

                    area_info = api.get_space_area(query)
                    area_reserve_info = api.get_area(date, query)
                    seat_count = area_info["count"]
                    seat_occupied = 0
                    if area_reserve_info:
                        seat_occupied = area_reserve_info["occupied"]
                    print(f"{bold}{query}{reset}")

                    print("신청 현황: ", end="")
                    print(
                        f"{bold}{yellow if seat_count>seat_occupied else red}{seat_occupied}{reset}/{bold}{seat_count}{reset}"
                    )
                    process_table(
                        area_info,
                        area_reserve_info,
                        highlight_seat,
                        config.get("student-id"),
                        False,
                    )
                elif len(query):
                    logger.error(f"'{query}': 올바르지 않은 검색어입니다.")
        else:
            logger.error("명령어를 입력하세요")
        config.save()
        if not repeat:
            exit(0)
    except KeyboardInterrupt:
        logger.info("\n종료")
        exit(0)
    except Exception as e:
        print(e)
        logger.info("명령 실행 실패.")
        if not repeat:
            exit(1)
