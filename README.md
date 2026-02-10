# AI Stock Technical Analyzer

使用 AI 大模型（Gemini / ChatGPT）对美股进行全面技术分析的 Web 应用。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)

## ✨ 功能特点

- 📈 **股票数据获取**：使用 yfinance 获取美股历史数据
- 📊 **专业K线图**：自动生成包含均线、RSI、MACD、布林带等指标的技术图表
- 🤖 **AI 智能分析**：将数据 + 图表发送给大模型进行多维度技术分析
- 🔄 **双模型支持**：支持 Gemini 和 ChatGPT 两种 AI 模型

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ai_stock_analyzer
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env`，填入你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-key
```

> 💡 只需配置你想使用的模型的 API 密钥即可

### 3. 运行应用

```bash
python app.py
```

访问 http://localhost:5000

## 📖 使用说明

1. 在输入框中输入美股代码（如 AAPL、NVDA、TSLA）
2. 选择数据周期（1个月 ~ 2年）
3. 选择 AI 模型（Gemini 或 ChatGPT）
4. 点击"开始分析"，等待 AI 返回技术分析结果

## 🔧 技术栈

- **后端**：Flask, yfinance, mplfinance, pandas
- **前端**：HTML5, CSS3, JavaScript
- **AI**：Google Gemini API, OpenAI API

## 📁 项目结构

```
ai_stock_analyzer/
├── app.py                 # Flask 主应用
├── stock_data.py          # 股票数据模块
├── chart_generator.py     # K线图生成
├── ai_analyzer.py         # AI 分析模块
├── config.py              # 配置管理
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
├── templates/
│   └── index.html         # 主页面
└── static/
    ├── style.css          # 样式
    ├── app.js             # 前端逻辑
    └── charts/            # 生成的图表
```

## ⚠️ 免责声明

本工具提供的技术分析仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。

## 📄 License

MIT License
