import requests
requests.packages.urllib3.disable_warnings()

from prettytable import PrettyTable
from concurrent.futures import ThreadPoolExecutor
import time
import os
import json
import argparse

import logging

sourceUrl = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?_='
sourceUrl_vpn = 'https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?vpn-12-o2-xk.bit.edu.cn&_='

infoPage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do'
infoPage_vpn = 'https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do?vpn-12-o2-xk.bit.edu.cn'

OutPlanCoursePage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?_='
OutPlanCoursePage_vpn = 'https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?vpn-12-o2-xk.bit.edu.cn&_='

InPlanCoursePage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?_='
InPlanCoursePage_vpn = 'https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?vpn-12-o2-xk.bit.edu.cn&_='

OutPlanCoursePath = './OutPlanCourses.json'
InPlanCoursePath = './InPlanCourses.json'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Cookie': ''  # add your cookie here
}

# add class info here
# this is examples
# you can copy it and change bjdm to your course
juzhen_zgc01_data = {
    'bjdm': '20231-17-1700002-1688866107858',
    'lx': '0',
    'csrfToken': '23b21ddb67914b3e81ae61923fd164aa'
}

courseList = [
    # add class info struct here
    
]


def printErr(string):
    print('\033[31m' + string + '\033[0m')


def printOK(string):
    print('\033[32m' + string + '\033[0m')


def setVPN():
    global sourceUrl, infoPage, InPlanCoursePage, OutPlanCoursePage
    sourceUrl = sourceUrl_vpn
    infoPage = infoPage_vpn
    InPlanCoursePage = InPlanCoursePage_vpn
    OutPlanCoursePage = OutPlanCoursePage_vpn


def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError as e:
        printErr("[-] Fail to catch courses. ERROR:" + str(e))
        return False


def postData(reqCourseList, req_data):
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

    req_data = {
        'query_keyword':        '',
        'query_kkyx':           '',
        'query_sfct':           '',
        'query_sfym':           '',
        'fixedAutoSubmitBug':   '',
        'pageIndex':            1,
        'pageSize':             1000,
        'sortField':            '',
        'sortOrder':            '',
    }

    print('[*] Try to catch courses out of plan...')

    timestamp = int(round(time.time() * 1000))
    reqCourseList = OutPlanCoursePage + str(timestamp)
    
    res = postData(reqCourseList, req_data)
    if not res:
        exit(1)
    if not is_valid_json(res.text):
        exit(1)
    
    with open(OutPlanCoursePath, 'w', encoding='utf8') as f:
        f.write(res.text)
    print('[+] Success. Courses have been saved in ' + OutPlanCoursePath)  

    print('[*] Try to catch courses in plan...')
    
    timestamp = int(round(time.time() * 1000))
    reqCourseList = InPlanCoursePage + str(timestamp)
    
    res = postData(reqCourseList, req_data)
    if not res:
        exit(1)
    if not is_valid_json(res.text):
        exit(1)
    
    with open(InPlanCoursePath, 'w', encoding='utf8') as f:
        f.write(res.text)
    print('[+] Success. Courses have been saved in ' + InPlanCoursePath)   


def findCourse(idList: list):
    with open(InPlanCoursePath, "r", encoding="utf8") as f:
        InPlanCourseInfo = f.read()
    InPlanCourseInfo = json.loads(InPlanCourseInfo)
    with open(OutPlanCoursePath, "r", encoding="utf8") as f:
        OutPlanCourseInfo = f.read()
    OutPlanCourseInfo = json.loads(OutPlanCourseInfo)

    targetList = []
    for id in idList:
        print("[*] Looking for course id:", id, "...")
        for info in InPlanCourseInfo['datas']:
            if id == info["KCDM"] and info["XQMC"] != "良乡校区" and ("非全" not in info["BJMC"]):
                targetList.append([info["KCMC"], info["RKJS"], "{}/{}".format(info["DQRS"], info["KXRS"])])
                courseList.append({'bjdm': info["BJDM"], 'lx': '0', 'csrfToken': ''})
        for info in OutPlanCourseInfo['datas']:
            if id == info["KCDM"] and info["XQMC"] != "良乡校区" and ("非全" not in info["BJMC"]):
                targetList.append([info["KCMC"], info["RKJS"], "{}/{}".format(info["DQRS"], info["KXRS"])])
                courseList.append({'bjdm': info["BJDM"], 'lx': '1', 'csrfToken': ''})

    if len(targetList) == 0:
        print("[!] No course found according to course id.")
        exit(0)

    table = PrettyTable()
    table.field_names = ['Name', 'Teachers', 'Chosen']
    table.add_rows(targetList)
    print("[+] Target courses showm as follow:")
    print(table)


def chooseCourse(course):
    while True:
        timestamp = int(round(time.time() * 1000))
        courseUrl = sourceUrl + str(timestamp)
        res = requests.post(url=courseUrl, data=course, headers=headers, verify=False)
        res = json.loads(res.text)
        if(res["code"] == 1):
            printOK("[+] A course is chosen! You can see on Web Browser!")
        else:
            logging.debug(res)
        time.sleep(0.01)


def start():
    print("[*] Start race...Please wait for servel hours...")
    pool = ThreadPoolExecutor(max_workers=len(courseList))
    for course in courseList:
        pool.submit(chooseCourse, course)
    
    while True:
        res = requests.get(url=infoPage, headers=headers, verify=False)
        csrfToken = json.loads(res.text)['csrfToken']
        for course in courseList:
            course['csrfToken'] = csrfToken
        time.sleep(60)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='BIT Course Race. A script to help masters get courses.')
    parser.add_argument("-c", "--cookie",
                         type=str,
                         dest="cookie",
                         help="Cookie copied from your web browser(after logging in sucessfully)")
    parser.add_argument("-i", "--courseID",
                         type=str,
                         dest="courseID",
                         nargs='+',
                         help="ID of courses, split with space")
    parser.add_argument("-v", "--vpn",
                         dest="vpn",
                         action='store_true',
                         help="if you choose course through webvpn, then use this")
    parser.add_argument("-d", "--debug",
                         dest="debug",
                         action='store_true',
                         help="if you want to show debug messages, then use this")
    
    args = parser.parse_args()
    headers['Cookie'] = args.cookie

    if args.vpn is True:
        setVPN()

    if args.debug is True:
        logging.basicConfig(level = logging.DEBUG,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    getCourseList()
    
    findCourse(args.courseID)

    start()
    
    # res = requests.get(url=infoPage, headers=headers, verify=False)
    # csrfToken = json.loads(res.text)['csrfToken']
    # for course in courseList:
    #     course['csrfToken'] = csrfToken
    