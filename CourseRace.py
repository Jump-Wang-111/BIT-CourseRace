import requests
from prettytable import PrettyTable
from concurrent.futures import ThreadPoolExecutor
import time
import os
import json
import argparse

requests.packages.urllib3.disable_warnings()
sourceUrl = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?_='
infoPage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do'
OutPlanCoursePage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?_='
InPlanCoursePage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?_='
OutPlanCoursePath = './OutPlanCourses.json'
InPlanCoursePath = './InPlanCourses.json'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Cookie': 'EMAP_LANG=zh; _WEU=qmZf97QOWWz0RhkB3cWfF8kxXxAnCMO8XGMI9OPDoT_sHIABqOub*zCB*MXoa0NlW0EUTfr7VZDiPqj0x28MxY1clsZ*BxBX; JSESSIONID=30E16605E409D96A020F31833BEB4419; route=ca1d7f4b7ee30cb5db90886138f378d1; XK_TOKEN=903d8dd2-a849-400a-9d76-1d73b8d0c18a'  # add your cookie here
}

# add class info here
# these three are examples
# you can copy them and change bjdm to your course
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
    try:
        res = requests.post(url=reqCourseList, data=req_data, headers=headers, verify=False)
        res.raise_for_status()
        with open(OutPlanCoursePath, 'w', encoding='utf8') as f:
            f.write(res.text)
        print('[+] Success. Courses have been saved in ' + OutPlanCoursePath)
    except requests.exceptions.HTTPError as errh:
        printErr("[-] Fail to catch courses. HTTP ERROR:" + errh)
    except requests.exceptions.ConnectionError as errc:
        printErr("[-] Fail to catch courses. Connection ERROR:" + errc)
    except requests.exceptions.Timeout as errt:
        printErr("[-] Fail to catch courses. Timeout ERROR:" + errt)
    except requests.exceptions.RequestException as err:
        printErr("[-] Fail to catch courses. Unknown ERROR:" + err)   

    print('[*] Try to catch courses in plan...')

    timestamp = int(round(time.time() * 1000))
    reqCourseList = InPlanCoursePage + str(timestamp)
    try:
        res = requests.post(url=reqCourseList, data=req_data, headers=headers, verify=False)
        res.raise_for_status()
        with open(InPlanCoursePath, 'w', encoding='utf8') as f:
            f.write(res.text)
        print('[+] Success. Courses have been saved in ' + InPlanCoursePath)
    except requests.exceptions.HTTPError as errh:
        printErr("[-] Fail to catch courses. HTTP ERROR:" + errh)
    except requests.exceptions.ConnectionError as errc:
        printErr("[-] Fail to catch courses. Connection ERROR:" + errc)
    except requests.exceptions.Timeout as errt:
        printErr("[-] Fail to catch courses. Timeout ERROR:" + errt)
    except requests.exceptions.RequestException as err:
        printErr("[-] Fail to catch courses. Unknown ERROR:" + err)   


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
                courseList.append({'bjdm': info["BJDM"], 'lx': '1', 'csrfToken': ''})
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
    args = parser.parse_args()
    headers['Cookie'] = args.cookie

    if not os.path.exists(InPlanCoursePath) or not os.path.exists(InPlanCoursePath):
        getCourseList()
    
    findCourse(args.courseID)

    start()
    
    # res = requests.get(url=infoPage, headers=headers, verify=False)
    # csrfToken = json.loads(res.text)['csrfToken']
    # for course in courseList:
    #     course['csrfToken'] = csrfToken

    # chooseCourse(courseList[3])
