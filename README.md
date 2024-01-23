# BIT-CourseRace

北京理工大学研究生抢课脚本，截止2024年1月测试有效

## Install

```shell
pip install -r requirements.txt
```

## Usage

​	运行脚本，指定cookie和课程代码，课程代码可以输入多个

```shell
usage: CourseRace.py [-h] [-c COOKIE] [-i COURSEID [COURSEID ...]]

BIT Course Race. A script to help masters get courses.

optional arguments:
  -h, --help            show this help message and exit
  -c COOKIE, --cookie COOKIE
                        Cookie copied from your web browser(after logging in sucessfully)
  -i COURSEID [COURSEID ...], --courseID COURSEID [COURSEID ...]
                        ID of courses, split with space
```

​	假设要选高级工程管理（0018002）、波动力学（0100002）和最优化理论与方法（1200008），那么使用方法如下：

```shell
 python .\CourseRace.py -c "EMAP_LANG=zh; _WEU=NZv8lxlDeSUU9noetDIbg7wUXlwPKSKHzWv_6inB1k4OjF5mYduW1tI7wo7I9H_hCifzuRRNlk7mWkpV2B4Ain4CusUEBuxJ; JSESSIONID=3CF142AEC95B962C9763E7208515C812; route=ca1d7f4b7ee30cb5db90886138f378d1; XK_TOKEN=3f77b3d5-eabd-4de1-bfc5-26eca9cef589" -i 0018002 0100002 1200008
```

## Usage by hand

​	脚本默认排除非全课程以及良乡课程，如果有相关需求、或出现脚本没能识别的课程，请用以下方式手动添加课程

1. 添加cookie

   ```python
   headers = {
       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
       'Cookie': ''  # add your cookie here
   }
   ```

2. 添加课程信息

   结构如下所示

   ```python
   # add class info here
   # this is example
   # you can copy it and change bjdm to your course
   juzhen_zgc01_data = {
       'bjdm': '20231-17-1700002-1688866107858',
       'lx': '0',
       'csrfToken': '23b21ddb67914b3e81ae61923fd164aa'
   }
   ```

   需要手动填写`bjdm`，选课按钮右键->检查，查找bjdm代码，位置如下

   ![image-20231012181121263](https://picgo-111.oss-cn-beijing.aliyuncs.com/img/image-20231012181121263.png)

3. 将课程信息加入列表

   ```python
   courseList = [
       # add class info struct here
       # eg:
       juzhen_zgc01_data,
       juzhen_zgc02_data,
       juzhen_zgc05_data
   ]
   ```


## PS

建议晚上24点前开始跑，卓有成效

然后第二天你会看到程序报错，这是正常的，因为一晚上cookie肯定过期了

所以如果白天跑了几个小时然后发现报错了，别慌，换个cookie然后重新跑就好了

~~理解一下，小脚本，哪有什么鲁棒性~~

