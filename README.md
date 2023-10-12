# BIT-CourseRace-2023-9

北京理工大学研究生抢课脚本，2023年9月版

## Usage

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

4. 安装依赖，运行脚本

## PS

建议晚上24点前开始跑，卓有成效

然后第二天你会看到程序报错，这是正常的，因为一晚上cookie肯定过期了

所以如果白天跑了几个小时然后发现报错了，别慌，更新个cookie然后重新跑就好了

~~理解一下，小脚本，哪有什么鲁棒性~~

