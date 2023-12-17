# Hanabi-AI-Assitant
## 简介
Hanabi-AI-Assitant（Hanabi小助手）是一个通过神经网络学习玩家对局行为来进行hanabi及其部分拓展玩法游戏的AI, 为了提高模型的易用性，我们将其接入了[hanabi.live](https://hanab.live/), 可以直接通过该网站的账号使用该Hanabi小助手加入对局或者观战对局，UI中会给出AI建议的操作。

Hanabi小助手的AI模型采用了类似[LLama2](https://github.com/karpathy/llama2.c/) 的模型结构，与hanabi.live服务器交互的逻辑主要参考了[Zamiell's example bot](https://github.com/Hanabi-Live/hanabi-live-bot/) 。训练的玩家数据来自[hanabi.live](https://hanab.live/) 上的部分玩家对局回放。

## 如何使用
你可以(1)选择直接使用打包好的release版，或者(2)下载源码,安装环境使用。如果不是进行二次开发，建议直接使用release版
### Release版使用说明
1. 根据自己的操作系统(目前只支持windows)在github上[下载Release版](https://github.com/UnbSky/Hanabi-AI-Assitant/releases)
2. 解压文件
3. 在```user_config.json```中填写自己的[hanabi.live](https://hanab.live/) 的账号和密码, model填写使用的模型，该文件具体格式如下:
```json
{
    "username": "your username",
    "password": "your password",
    "model": "model/HHmodel_v1_s56"
}
```
4. 点击```main_connect.exe```启动
5. 页面的主要功能介绍如下所示:

### 源码及环境说明
1. 下载源码
2. 使用任何包含python3的环境(建议python版本>=3.8)
3. 使用```pip install -r requirements.txt``` 安装所有需要的环境
4. 在```user_config.json```中填写自己的[hanabi.live](https://hanab.live/) 的账号和密码
5. 运行```main_connect.py```启动UI界面

## 模型介绍
模型目前支持2-5人对战的14种玩法，AI自己和自己对战的具体得分如下，每一行的条件测试数据为500局
## 其他
 在 [这里](https://github.com/UnbSky/Hanabi-AI-Assitant/issues) 写下出现的问题或者建议

