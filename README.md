
# otogedb-convert

## ⭐️ 介绍

将otogedb中的数据转换为水鱼数据的格式

## 🚀 开始

> [!NOTE]
> Need Python version 3.9 or above

安装`requirements.txt`中需要的依赖
```sh
pip install -r requirements.txt
```

## ✨ 使用

运行`convert.py`文件，运行完成之后会在本地产生`convert_music_data.json`即为目标数据

## ⚠️ 说明
本项目通过`music_data/mapping.json`文件中个各版本的时间范围进行版本号转换

版本更新时请修改`NEW_VERSION`和`NEW_VERSION_RELEASES_DATE`两个常量为当前版本正确值

同时在`music_data/mapping.json`文件中添加最新版本的信息

本项目转换数据格式后，会同时抓取水鱼查分器的music_data数据将otogedb中缺失的exp和bas谱面的数据进行补全覆盖

最后会通过本项目的`music_data/origin_music_data.json`文件替换id为数字id

期待修改`origin_music_data.json`中的字符串id数据为真实的数字id数据并PR
