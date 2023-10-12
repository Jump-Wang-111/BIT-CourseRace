import requests
from loguru import logger
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
import json

sourceUrl = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?_='
infoPage = 'https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Cookie': ''  # add your cookie here
}
# proxies = {
#     "http": "http://127.0.0.1:7890",
#     "https": "http://127.0.0.1:7890",
# }

# add class info here
juzhen_zgc01_data = {
    'bjdm': '20231-17-1700002-1688866107858',
    'lx': '0',
    'csrfToken': '23b21ddb67914b3e81ae61923fd164aa'
}
juzhen_zgc02_data = {
    'bjdm': '90b0346296cf46a49d92e686c65c05fc',
    'lx': '0',
    'csrfToken': '23b21ddb67914b3e81ae61923fd164aa'
}
juzhen_zgc05_data = {
    'bjdm': 'b09e48ec14b54069bec0cb509925c937',
    'lx': '0',
    'csrfToken': '23b21ddb67914b3e81ae61923fd164aa'
}

courseList = [
    # add class info struct here
    # juzhen_zgc01_data,
    # juzhen_zgc02_data,
    # juzhen_zgc05_data
]

def chooseCourse(course):
    while True:
        timestamp = int(round(time.time() * 1000))
        courseUrl = sourceUrl + str(timestamp)
        req = requests.post(url=courseUrl, data=course, headers=headers, verify=False)
        logger.info(req.text)
        time.sleep(0.01)


if __name__ == '__main__':
    
    pool = ThreadPoolExecutor(max_workers=len(courseList))
    for course in courseList:
        pool.submit(chooseCourse, course)
    
    while True:
        req = requests.get(url=infoPage, headers=headers, verify=False)
        csrfToken = json.loads(req.text)['csrfToken']
        for course in courseList:
            course['csrfToken'] = csrfToken
        logger.info('new csrfToken: ' + csrfToken)
        time.sleep(60)

