# Edge-TTS HTTP 服务

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Microsoft Edge TTS 引擎的 HTTP 服务，通过 RESTful API 提供文字转语音功能，支持多语言和多种声音。

[English](README.md) | [中文](README_zh.md)

## 特性

- 🌍 支持多种语言和声音
- 🚀 支持流式和非流式音频输出
- 📦 长文本存储和 ID 调用（避免 URL 过长）
- 🔧 简单的 REST API 接口
- 🐳 支持 Docker 部署
- ⚡ 低延迟响应
- ⏳ 自动清理过期文本（1 分钟有效期）

## 快速开始

### 方式一：直接运行

1. 克隆仓库：

```bash
git clone https://github.com/doctoroyy/edge-tts-as-a-service
cd edge-tts-as-a-service
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 启动服务：

```bash
python main.py
```

服务将在 http://localhost:5000 启动

### 方式二：Docker 部署

1. 构建镜像：

```bash
docker build -t edge-tts-as-a-service .
```

2. 运行容器：

```bash
docker run -d -p 5000:5000 edge-tts-as-a-service
```

API 文档

1. 获取可用声音列表
   获取所有支持的声音选项。

`GET /voices`

响应示例：

```json
{
  "code": 200,
  "message": "OK",
  "data": [
    {
      "Name": "zh-CN-YunxiNeural",
      "ShortName": "zh-CN-YunxiNeural",
      "Gender": "Male",
      "Locale": "zh-CN"
    }
    // ... 更多声音选项
  ]
}
```

2. 存储长文本（新增）
   存储长文本并获取调用 ID，解决 URL 长度限制问题。

`POST /tts/store`

请求体：

```json
{
  "text": "这里是非常长的文本内容..."
}
```

响应示例：

```json
{
  "code": 200,
  "message": "OK",
  "data": {
    "text_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

3. 文本转语音（下载）
   将文本转换为语音文件并下载，支持直接文本或存储 ID 调用。

`POST /tts`

请求体：

```json
{
  "text": "你好，世界！", // 文本内容（与text_id二选一）
  "text_id": "存储的文本ID", // 存储的文本ID（与text二选一）
  "voice": "zh-CN-YunxiNeural", // 可选，默认为 "zh-CN-YunxiNeural"
  "file_name": "hello.mp3" // 可选，默认为 "test.mp3"
}
```

响应：

Content-Type: audio/mpeg

返回音频文件流

4. 文本转语音（流式）

`POST /tts/stream`

请求体：

```json
{
  "text": "你好，世界！", // 文本内容（与text_id二选一）
  "text_id": "存储的文本ID", // 存储的文本ID（与text二选一）
  "voice": "zh-CN-YunxiNeural", // 可选，默认为 "zh-CN-YunxiNeural"
  "rate": "+0%", // 可选，默认为 "+0%"
  "pitch": "+0Hz" // 可选，默认为 "+0Hz"
}
```

响应：

Content-Type: application/octet-stream

返回音频数据流
