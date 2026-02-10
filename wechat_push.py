"""
AI Stock Analyzer - WeChat Push Notification via Server酱
使用方法: python wechat_push.py AAPL NVDA TSLA
"""
import sys
import os
import requests
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from stock_data import get_stock_data, format_data_for_ai
from chart_generator import generate_chart
from ai_analyzer import analyze_stock
import config  # This loads .env via dotenv


# Server酱配置 (must be after config import which loads .env)
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")


def send_wechat(title: str, content: str) -> bool:
    """通过Server酱发送微信消息"""
    if not SERVERCHAN_KEY:
        print("❌ 错误: 未配置 SERVERCHAN_KEY")
        print("请在 .env 文件中添加: SERVERCHAN_KEY=你的SendKey")
        return False
    
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = {
        "title": title,
        "desp": content.replace("\n", "\n\n")  # Markdown 需要双换行
    }
    
    try:
        response = requests.post(url, data=data, timeout=30)
        result = response.json()
        
        if result.get("code") == 0:
            print("✅ 微信推送成功!")
            return True
        else:
            print(f"❌ 推送失败: {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def analyze_and_push(symbol: str, period: str = "2y", model: str = "gemini-flash") -> bool:
    """分析股票并推送到微信"""
    print(f"\n📊 正在分析 {symbol}...")
    
    # 1. 获取股票数据
    stock_data = get_stock_data(symbol, period)
    if not stock_data.get("success"):
        print(f"❌ 获取数据失败: {stock_data.get('error')}")
        return False
    
    # 2. 生成K线图
    raw_df = stock_data.pop("raw_df")
    chart_path = generate_chart(raw_df, symbol)
    print(f"📈 K线图已生成: {chart_path}")
    
    # 3. 格式化数据
    data_text = format_data_for_ai({**stock_data, 'data': stock_data['data']})
    
    # 4. AI 分析
    print(f"🤖 正在使用 {model} 进行分析...")
    analysis_result = analyze_stock(
        data_text=data_text,
        image_path=chart_path,
        symbol=symbol,
        model=model
    )
    
    if not analysis_result.get("success"):
        print(f"❌ AI分析失败: {analysis_result.get('error')}")
        return False
    
    # 5. 构建推送内容
    info = stock_data.get("info", {})
    stats = stock_data.get("stats", {})
    
    title = f"📊 {symbol} AI技术分析 - ${stats.get('latest_close', 'N/A')}"
    
    content = f"""## {info.get('name', symbol)} ({symbol})

**当前价格**: ${stats.get('latest_close', 'N/A')}
**区间涨跌**: {stats.get('period_change', 'N/A')}%
**分析周期**: {period}
**AI模型**: {analysis_result.get('model', model)}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{analysis_result.get('analysis', '分析结果为空')}

---
*本分析由AI生成，仅供参考，不构成投资建议*
"""
    
    # 6. 发送微信
    return send_wechat(title, content)


def main():
    """主函数"""
    # 解析命令行参数
    if len(sys.argv) < 2:
        print("用法: python wechat_push.py <股票代码> [股票代码2] ...")
        print("示例: python wechat_push.py AAPL NVDA TSLA")
        print("\n可选环境变量:")
        print("  SERVERCHAN_KEY  - Server酱的SendKey")
        print("  PERIOD          - 数据周期 (默认: 2y)")
        print("  MODEL           - AI模型 (默认: gemini-flash)")
        return
    
    symbols = [s.upper() for s in sys.argv[1:]]
    period = os.getenv("PERIOD", "2y")
    model = os.getenv("MODEL", "gemini-flash")
    
    print(f"=" * 50)
    print(f"🚀 AI Stock Analyzer - WeChat Push")
    print(f"=" * 50)
    print(f"📋 股票列表: {', '.join(symbols)}")
    print(f"📅 数据周期: {period}")
    print(f"🤖 AI模型: {model}")
    print(f"=" * 50)
    
    success_count = 0
    for symbol in symbols:
        if analyze_and_push(symbol, period, model):
            success_count += 1
    
    print(f"\n{'=' * 50}")
    print(f"✅ 完成! 成功推送 {success_count}/{len(symbols)} 个股票分析")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
