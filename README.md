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