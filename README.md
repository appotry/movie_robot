更新日志
=========================
- 2022-01-12
  - MTeam支持Cookie登陆，无需配置账号密码
  - 新增可配置检索条件，按首发种子发布已过时间进行过滤；一部刚出种子的电影，首个种子的质量往往不是特别好，没有选择余地，如果等上几个小时，好片源种子可能会同步发出来。这个参数就是为了解决这个痛点而设计，如果你只为首发不挑片源，可以删除此配置项或者设置为null即可跳过验证；


功能介绍
=========================
**公告：如果有其他PT大站邀请的小伙伴，可以加微信发个邀请，有助于开发扩展多站同时检索的功能。也欢迎感兴趣懂开发的小伙伴共同完善！**

定时自动从豆瓣电影的想看、在看、看过中获取影音信息，然后去PT站自动检索种子，找到最佳资源后按豆瓣电影分类提交到BT下载工具下载。在下载前，会自动检查你的Emby中是否已经存在。
基于此功能机制，还顺带具备了下列功能：
- 将一部刚上映，或者还没上映的电影加入想看，当PT站更新时会第一时间帮你下好，被Emby扫描到后直接观看。
- 对剧集类型的影视资源，如果你正在看一部没更新完的剧，只要pt站更新，也会帮你对比本地影音库缺少的剧集开始自动下载。

**注意，豆瓣和PT的读取和检索，均未使用OpenAPI（如有任何合规问题请及时联系作者下架源码），但模拟请求的过程中，增加了随机延迟机制来保护网站。本工具只能用于学习和自己研究，禁止用作任何商业用途！**

Emby个人影音库
<img src="https://raw.githubusercontent.com/pofey/movie_robot/main/doc/embyweb.jpg" width="860" height="500" style="float: left;"/>

环境要求
=========================
- 影视剧集管理服务器：Emby
- BT下载工具：qbittorrent
- 你需要拥有一个PT站的账号：MTeam（当前仅支持mteam种子自动检索）

如果你恰好是上面的影音方案，就可以直接开始使用了。

部署方式
=========================
- 本应用支持Docker形式启动，日常运行占资源非常低，无CPU消耗（linux crontab调度任务），常驻内存2MB左右；但因为使用了非OpenAPI的形式，所以没有提供打包好的docker镜像进行分享，请自行通过Dockerfile打包；
  - linux/mac: sh docker_build 进行打包
- 当然也可以下载源码，直接用NAS的定时任务运行，或者你的任何能够定时调度python程序的工具；
  - 1、python3 -m venv venv 创建虚拟环境
  - 2、安装依赖：pip install -r requirements.txt 
  - 3、执行命令：python3 douban_movie_download.py -w /workdir


配置文件
=========================
通过任何形式第一次运行应用时，都会在你指定的工作目录帮助创建一个user_config.yml文件，当然你也可以按源码的doc/user_config.yml模版提前创建，在这个文件中描述了很多注释讲解配置方式。

打赏作者杯咖啡
=========================
你的支持，是持续完善的动力。

<img src="https://raw.githubusercontent.com/pofey/movie_robot/main/doc/wechatpay.jpg" width="220" height="220" alt="赞赏码" style="float: left;"/>

打赏过的，交个朋友：

<img src="https://github.com/pofey/movie_robot/raw/main/doc/wechat.JPG" width="244" height="314" alt="微信" style="float: left;"/>
