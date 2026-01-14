# aujc

## 20250327

提供自己训练模型，优化点选验证码通过率，aujc_trainer项目：[https://github.com/icepage/aujc_trainer](https://github.com/icepage/aujc_trainer)

训练完后有onnx和charsets.json文件，docker启动可以通过挂载方式使用

```python
docker run -i \
    -v $PWD/config.py:/app/config.py \
    -v $PWD/myocr_v1.onnx:/app/myocr_v1.onnx \
    -v $PWD/charsets.json:/app/charsets.json \
    icepage/aujc:latest python main.py
```

## 介绍
- 用来自动化更新青龙面板的失效JD_COOKIE, 主要有三步
    - 自动检测并获取青龙面板的失效JD_COOKIE;
    - 拿到失效JD_COOKIE内容后, 根据配置的账号信息, 自动化登录JD页面, 拿到key;
    - 根据拿到的key, 自动化更新青龙面板的失效JD_COOKIE。
- 支持的验证码类型有：
  - 滑块验证码;
  - 形状颜色验证码(基本不会出现了);
  - 点选验证码;
  - 短信验证码,支持手动输入和webhook(首次登录大概率出现, 其它时间出现频率低。webhook配置流程繁琐, 不爱折腾的建议使用手动输入或关闭。)
  - 手机语音识别验证码
- 支持的账号类型有：
  - 账号密码登录
  - QQ登录
- python >= 3.9 (playwright依赖的typing，在3.7和3.8会报错typing.NoReturn的BUG)
- 支持windows,linux(无GUI)
- 支持docker部署
- 支持代理
- 支持Web管理界面
- linux无GUI使用文档请转向 [linux无GUI使用文档](https://github.com/icepage/AutoUpdateJdCookie/blob/main/README.linux.md)
- WINDOWS整体效果如下图

![GIF](./img/main.gif)


## 使用文档

### 1、Docker Compose部署（推荐）

使用Docker Compose可以简化部署流程，同时管理Web界面和定时任务。

#### 1.1 准备工作

1. 克隆项目到本地
   ```bash
   git clone https://github.com/icepage/AutoUpdateJdCookie.git
   cd AutoUpdateJdCookie
   ```

2. 生成配置文件
   ```bash
   docker run -i --rm \
     -v $PWD/config.py:/app/config.py \
     icepage/aujc python make_config.py
   ```

3. 配置文件说明
   - 执行`make_config.py`后，会生成`config.py`文件
   - 详细配置说明请参考 [配置文件说明](https://github.com/icepage/AutoUpdateJdCookie/blob/main/配置文件说明.md)
   - Linux的**无头模式(headless)一定要设为True!!!!**

#### 1.2 启动服务

1. 使用Docker Compose启动服务
   ```bash
   docker-compose up -d
   ```

2. 查看服务状态
   ```bash
   docker-compose ps
   ```

3. 查看日志
   ```bash
   # 查看Web服务日志
   docker-compose logs -f app
   
   # 查看定时任务日志
   docker-compose logs -f scheduler
   ```

4. 停止服务
   ```bash
   docker-compose down
   ```

#### 1.3 访问Web管理界面

服务启动后，可以通过以下地址访问Web管理界面：

```
http://<服务器IP>:8686
```

Web管理界面提供了以下功能：
- 查看系统状态
- 管理账号配置
- 查看任务日志
- 手动触发更新任务

### 1.4 自定义配置

可以通过修改`docker-compose.yml`文件来自定义配置：

- **端口映射**：默认映射到宿主机8686端口，可以根据需要修改
- **环境变量**：可以通过环境变量覆盖配置文件中的设置
- **挂载卷**：可以挂载自定义的模型文件和配置文件

### 2、传统Docker部署

### 下载镜像
```shell
docker pull icepage/aujc:latest
```

### 生成config.py
```python
# 新建一个config.py
touch config.py
# 执行生成make_config.py, 记得最后要按y覆盖config.py
docker run -i --rm \
  -v $PWD/config.py:/app/config.py \
  icepage/aujc python make_config.py
```

说明：
- 执行make_config.py, 会生成config.py
- config.py的说明请转向 [配置文件说明](https://github.com/icepage/AutoUpdateJdCookie/blob/main/配置文件说明.md)
- Linux的**无头模式(headless)一定要设为True!!!!**
- 如果不会python的，参考config_example.py, 自己配置一个config.py, 我们基于这个config.py运行程序;

### 手动执行
- 2种场景下需要手动
  - 1、需要短信验证时需要手动, 本应用在新设备首次更新时必现. 
  - 2、定时时间外需要执行脚本. 
- 配置中的sms_func设为manual_input时, 才能在终端填入短信验证码。
- 当需要手动输入验证码时, docker运行需加-i参数。否则在触发短信验证码时会报错Operation not permitted
```bash
docker run -i -v $PWD/config.py:/app/config.py icepage/aujc:latest python main.py
```

![PNG](./img/linux.png)

### 长期运行
- 程序读config.py中的cron_expression, 定期进行更新任务
- 当sms_func设置为manual_input, 长期运行时会自动将manual_input转成no，避免滥发短信验证码, 因为没地方可填验证码. 
```bash
docker run -v $PWD/config.py:/app/config.py icepage/aujc:latest
```

## 3、青龙 Debian 容器内一键安装

- 仅测试 **whyour/qinglong:debian**
- 支持 ARM64 和 AMD64 架构
````shell
bash <(curl -fsSL "https://raw.githubusercontent.com/icepage/AutoUpdateJdCookie/main/AutoUpdateJdCookie_install.sh")
````


## 4、本地部署
### 安装依赖
```commandline
pip install -r requirements.txt
```

### 安装chromium插件
```commandline
playwright install chromium
```

### 生成config.py
```python
python make_config.py
```

说明：
- 执行make_config.py, 会生成config.py
- config.py的说明请转向 [配置文件说明](https://github.com/icepage/AutoUpdateJdCookie/blob/main/配置文件说明.md)
- 如果不会python的，参考config_example.py, 自己配置一个config.py, 我们基于这个config.py运行程序;

### 运行脚本
#### 1、单次手动执行
```commandline
python main.py
```

#### 2、常驻进程
进程会读取config.py里的cron_expression,定期进行更新任务
```commandline
python schedule_main.py
```

## 特别感谢
- 感谢 [所有赞助本项目的热心网友 --> 打赏名单](https://github.com/icepage/AutoUpdateJdCookie/wiki/%E6%89%93%E8%B5%8F%E5%90%8D%E5%8D%95)
- 感谢 **https://github.com/sml2h3/ddddocr** 项目，牛逼项目
- 感谢 **https://github.com/zzhjj/svjdck** 项目，牛逼项目

## 创作不易，如果项目有帮助到你，大佬点个星或打个赏吧
![JPG](./img/w.jpg)
