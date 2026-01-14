import argparse
import json
import logging
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, TypedDict, cast

import requests
from prettytable import PrettyTable
from rich.live import Live
from rich.table import Table
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)  # 只忽略 InsecureRequestWarning
# requests.packages.urllib3.disable_warnings()

stop_event = threading.Event()

sourceUrl = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?_="
sourceUrl_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?vpn-12-o2-xk.bit.edu.cn&_="

infoPage = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do"
infoPage_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do?vpn-12-o2-xk.bit.edu.cn"

OutPlanCoursePage = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?_="
OutPlanCoursePage_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?vpn-12-o2-xk.bit.edu.cn&_="

InPlanCoursePage = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?_="
InPlanCoursePage_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?vpn-12-o2-xk.bit.edu.cn&_="

OutPlanCoursePath = "./OutPlanCourses.json"
InPlanCoursePath = "./InPlanCourses.json"

# ================================= 手动添加课程信息 ================================
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Cookie": "",
}


class CourseInfo(TypedDict):
    bjdm: str
    lx: str
    csrfToken: str  # auto detect


# add class info here
# this is examples
# you can copy it and change bjdm to your course
juzhen_zgc01_data: CourseInfo = {
    "bjdm": "20231-17-1700002-1688866107858",
    "lx": "0",  # 计划内0 / 计划外1
    "csrfToken": "",
}

courseList: List[CourseInfo] = [
    # juzhen_zgc01_data
    # add class info struct here
]
# ================================================================================


class StatusInfo(TypedDict):
    bjmc: str
    success: int
    fail: int


status: Dict[str, StatusInfo] = {}


def printErr(string: str):
    print("\033[31m" + string + "\033[0m")


def printOK(string: str):
    print("\033[32m" + string + "\033[0m")


def setVPN():
    global sourceUrl, infoPage, InPlanCoursePage, OutPlanCoursePage
    sourceUrl = sourceUrl_vpn
    infoPage = infoPage_vpn
    InPlanCoursePage = InPlanCoursePage_vpn
    OutPlanCoursePage = OutPlanCoursePage_vpn


def is_valid_json(json_str: str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError as e:
        printErr("[-] Fail to catch courses. ERROR:" + str(e))
        return False


def postData(reqCourseList: str, req_data: Dict[str, str | int]):
    try:
        res = requests.post(url=reqCourseList, data=req_data, headers=headers, verify=False)
        res.raise_for_status()
        return res
    except requests.exceptions.HTTPError as errh:
        printErr("[-] Fail to catch courses. HTTP ERROR:" + str(errh))
    except requests.exceptions.ConnectionError as errc:
        printErr("[-] Fail to catch courses. Connection ERROR:" + str(errc))
    except requests.exceptions.Timeout as errt:
        printErr("[-] Fail to catch courses. Timeout ERROR:" + str(errt))
    except requests.exceptions.RequestException as err:
        printErr("[-] Fail to catch courses. Unknown ERROR:" + str(err))

    return None


def getCourseList():
    req_data: Dict[str, int | str] = {
        "query_keyword": "",
        "query_kkyx": "",
        "query_sfct": "",
        "query_sfym": "",
        "fixedAutoSubmitBug": "",
        "pageIndex": 1,
        "pageSize": 1000,
        "sortField": "",
        "sortOrder": "",
    }

    print("[*] Try to catch courses out of plan...")

    timestamp = int(round(time.time() * 1000))
    reqCourseList = OutPlanCoursePage + str(timestamp)

    res = postData(reqCourseList, req_data)
    if not res:
        exit(1)
    if not is_valid_json(res.text):
        exit(1)

    with open(OutPlanCoursePath, "w", encoding="utf8") as f:
        f.write(res.text)
    print("[+] Success. Courses have been saved in " + OutPlanCoursePath)

    print("[*] Try to catch courses in plan...")

    timestamp = int(round(time.time() * 1000))
    reqCourseList = InPlanCoursePage + str(timestamp)

    res = postData(reqCourseList, req_data)
    if not res:
        exit(1)
    if not is_valid_json(res.text):
        exit(1)

    with open(InPlanCoursePath, "w", encoding="utf8") as f:
        f.write(res.text)
    print("[+] Success. Courses have been saved in " + InPlanCoursePath)


def findCourse(idList: List[str], XQMC: str):
    with open(InPlanCoursePath, "r", encoding="utf8") as f:
        InPlanCourseInfoFile = f.read()
    InPlanCourseInfo = json.loads(InPlanCourseInfoFile)
    with open(OutPlanCoursePath, "r", encoding="utf8") as f:
        OutPlanCourseInfoFile = f.read()
    OutPlanCourseInfo = json.loads(OutPlanCourseInfoFile)

    targetList: List[List[str]] = []
    for id in idList:
        print("[*] Looking for course id:", id, "...")
        for info in InPlanCourseInfo["datas"]:
            if id == info["KCDM"] and info["XQMC"] == XQMC and ("非全" not in info["BJMC"]):
                targetList.append([info["BJMC"], info["RKJS"], "{}/{}".format(info["DQRS"], info["KXRS"])])
                courseList.append({"bjdm": info["BJDM"], "lx": "0", "csrfToken": ""})
                status[info["BJDM"]] = {"bjmc": info["BJMC"], "success": 0, "fail": 0}
        for info in OutPlanCourseInfo["datas"]:
            if id == info["KCDM"] and info["XQMC"] == XQMC and ("非全" not in info["BJMC"]):
                targetList.append([info["BJMC"], info["RKJS"], "{}/{}".format(info["DQRS"], info["KXRS"])])
                courseList.append({"bjdm": info["BJDM"], "lx": "1", "csrfToken": ""})
                status[info["BJDM"]] = {"bjmc": info["BJMC"], "success": 0, "fail": 0}

    for course in courseList:
        # 前面手动添加的课程信息，在信息中搜索
        if course["bjdm"] not in status:
            searched = (
                c
                if (
                    c := next((info for info in InPlanCourseInfo["datas"] if info["BJDM"] == course["bjdm"]), None)
                    is not None
                )
                else next((info for info in OutPlanCourseInfo["datas"] if info["BJDM"] == course["bjdm"]), None)
            )
            if searched is not None:
                searched = cast(Dict[str, str], searched)
                targetList.append(
                    [searched["BJMC"], searched["RKJS"], "{}/{}".format(searched["DQRS"], searched["KXRS"])]
                )
                status[course["bjdm"]] = {"bjmc": searched["BJMC"], "success": 0, "fail": 0}
            else:
                # 没搜索到，姑且还是添加进来进行请求，未测试可行性
                status[course["bjdm"]] = {"bjmc": course["bjdm"], "success": 0, "fail": 0}

    if len(targetList) == 0:
        print("[!] No course found according to course id.")
        if len(courseList) == 0:
            print("[!] No course need to be chosen.")
            exit(0)
    else:
        table = PrettyTable()
        table.field_names = ["Name", "Teachers", "Chosen"]
        table.align["Name"] = "l"  # type: ignore
        table.add_rows(targetList)  # type: ignore
        print("[+] Target courses showm as follow:")
        print(table)


def chooseCourse(course: CourseInfo):
    while not stop_event.is_set():
        timestamp = int(round(time.time() * 1000))
        courseUrl = sourceUrl + str(timestamp)
        res = requests.post(url=courseUrl, data=course, headers=headers, verify=False)
        res = json.loads(res.text)
        if res["code"] == 1:
            printOK(f"[+] A course is chosen! You can see on Web Browser! [{status[course['bjdm']]['bjmc']}]")
            status[course["bjdm"]]["success"] += 1
        else:
            logging.debug(res)
            status[course["bjdm"]]["fail"] += 1
        time.sleep(0.01)


def make_status_table():
    table = Table(title="Status")
    table.add_column("Name", justify="center")
    table.add_column("S", justify="center")
    table.add_column("F", justify="center")

    for _, s in status.items():
        table.add_row(s["bjmc"], str(s["success"]), str(s["fail"]))
    return table


def start():
    print("[*] Start race...Please wait for servel hours...")
    with ThreadPoolExecutor(max_workers=len(courseList)) as pool:
        for course in courseList:
            pool.submit(chooseCourse, course)

        heartbeat = 0
        live = Live(make_status_table(), refresh_per_second=2)
        live.start()
        try:
            while not stop_event.is_set():
                if heartbeat % 30 == 0:
                    try:
                        res = requests.get(url=infoPage, headers=headers, verify=False)
                        csrfToken = json.loads(res.text)["csrfToken"]
                        for course in courseList:
                            course["csrfToken"] = csrfToken
                    except Exception as e:
                        print(f"[ERROR] refresh token failed: {e}")

                live.update(make_status_table())
                time.sleep(2)
                heartbeat += 1
        except KeyboardInterrupt:
            print("[*] Ctrl+C pressed, stopping all threads...")
            stop_event.set()
        finally:
            live.stop()


def get_cookie_from_browser(login_url: str = "https://sso.bit.edu.cn/cas/login?service=https:%2F%2Fxk.bit.edu.cn%2Fyjsxkapp%2Fsys%2Fxsxkappbit%2F*default%2Findex.do", 
                            timeout: int = 300) -> Optional[str]:

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[*] Playwright模块未安装。请先运行: pip install playwright或取消--auto-login选项")
        return None
    

    print("[*]正在启动浏览器")
    print("[*]请在浏览器中完成登录操作，登录成功后程序将自动获取Cookie")
    
    cookie_str = None
    
    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled', 
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720}
            )

            page = context.new_page()
            
            print(f"[*] 正在打开登录页面: {login_url}")
            page.goto(login_url)
            
            print("[!] 等待用户登录...")
            print("[!] 提示: 登录成功后，页面URL会发生变化，程序将自动检测\n")
            
            # 等待用户登录
            start_time = time.time()
            last_url = page.url

            
            #循环
            while time.time() - start_time < timeout:
                try:
                    current_url = page.url
                    
                    # 检测URL是否变化（可能已登录）
                    if current_url != last_url:
                        print(f"[*] 检测到页面跳转: {current_url}")
                        last_url = current_url
                    
                    # 获取所有Cookie
                    cookies = context.cookies()
                    
                    # 检查是否有关键Cookie
                    has_session_cookie = any(
                        cookie.get('name') in ['GS_SESSIONID'] 
                        for cookie in cookies
                    )
                    
                    if has_session_cookie :

                        cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
                        
    
                        print("[*]  Cookie获取成功!")
                        break
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"[!] 检测过程中出现错误: {e}")
                    time.sleep(1)
            
            if cookie_str is None:
                print(f"\n[!] 超时: 未在 {timeout} 秒内检测到登录")
                print("[!] 请确保您已完成登录操作\n")
            
            # 关闭浏览器
            browser.close()
            
    except Exception as e:
        print(f"\n[-] ❌ 启动浏览器失败: {e}")
        print("[!] 请确保已安装Playwright:")
        print("    pip install playwright")
        print("    playwright install chromium\n")
        return None
    
    return cookie_str


if __name__ == "__main__":

    @dataclass
    class Args:
        cookie: Optional[str]
        courseID: Optional[List[str]]
        vpn: bool
        liangxiang: bool
        debug: bool
        auto_login: bool

    parser = argparse.ArgumentParser(description="BIT Course Race. A script to help masters get courses.")
    parser.add_argument(
        "-c",
        "--cookie",
        type=str,
        required=False,
        dest="cookie",
        help="Cookie copied from your web browser(after logging in sucessfully)",
    )
    parser.add_argument(
        "-a",
        "--auto-login",
        dest="auto_login",
        action="store_true",
        help="Automatically open browser with Playwright to get cookie (recommended)",
    )
    parser.add_argument(
        "-i", "--courseID", type=str, dest="courseID", nargs="+", help="ID of courses, split with space"
    )
    parser.add_argument(
        "-v", "--vpn", dest="vpn", action="store_true", help="if you choose course through webvpn, then use this"
    )
    parser.add_argument(
        "-l", "--liangxiang", dest="liangxiang", action="store_true", help="switch campuses to Liangxiang campuses"
    )
    parser.add_argument(
        "-d", "--debug", dest="debug", action="store_true", help="if you want to show debug messages, then use this"
    )
    parsed = parser.parse_args()
    args: Args = Args(
        cookie=parsed.cookie, courseID=parsed.courseID, vpn=parsed.vpn, 
        liangxiang=parsed.liangxiang, debug=parsed.debug, auto_login=parsed.auto_login
    )

    # 如果启用自动登录
    if args.auto_login:
        print("[*] 启动Playwright自动登录模式...")

        # 根据是否使用VPN选择不同的登录URL
        if args.vpn:
            login_url = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/*default/index.do?vpn-12-o2-xk.bit.edu.cn"
        else:
            login_url = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/*default/index.do"
        
        cookie = get_cookie_from_browser()
        
        if cookie:
            args.cookie = cookie
            headers["Cookie"] = cookie
        else:
            printErr("\n[-] 自动获取Cookie失败")
            printErr("[-] 您可以:")
            printErr("    1. 重新运行程序并使用 -a 参数再试一次")
            printErr("    2. 手动获取Cookie后使用 -c 参数")
            printErr("\n示例: python CourseRace.py -c \"你的Cookie\" -i 课程ID\n")
            exit(1)

    elif not args.cookie:
        printErr("\n[-] 错误: 未提供Cookie")
        printErr("[-] 请选择以下方式之一:")
        printErr("    1. 使用自动登录: python CourseRace.py -a -i 课程ID")
        printErr("    2. 手动提供Cookie: python CourseRace.py -c \"你的Cookie\" -i 课程ID\n")
        parser.print_help()
        exit(1)
    else:
        headers["Cookie"] = args.cookie

    if args.vpn is True:
        setVPN()

    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    getCourseList()

    findCourse(
        args.courseID if args.courseID else [],
        "良乡校区" if args.liangxiang else "中关村校区",
    )

    start()

    # res = requests.get(url=infoPage, headers=headers, verify=False)
    # csrfToken = json.loads(res.text)['csrfToken']
    # for course in courseList:
    #     course['csrfToken'] = csrfToken
