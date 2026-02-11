"""
AI Stock Technical Analyzer - Flask Web Application
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import traceback

from stock_data import get_stock_data, format_data_for_ai
from chart_generator import generate_all_charts, cleanup_old_charts
from ai_analyzer import analyze_stock
import config

app = Flask(__name__)

# Ensure charts directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'charts'), exist_ok=True)


# Global error handlers — always return JSON, never HTML
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "success": False}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": f"Internal server error: {str(e)}", "success": False}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()
    return jsonify({"error": f"Unexpected error: {str(e)}", "success": False}), 500


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Main analysis endpoint
    
    Expects JSON body:
    {
        "symbol": "AAPL",
        "period": "6mo",
        "model": "gemini"
    }
    """
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        period = data.get('period', '6mo')
        model = data.get('model', 'gemini')
        
        if not symbol:
            return jsonify({"error": "Stock symbol is required", "success": False}), 400
        
        print(f"\n{'='*50}")
        print(f"[API] Analyze request: symbol={symbol}, period={period}, model={model}")
        print(f"{'='*50}")
        
        # Cleanup old charts
        cleanup_old_charts(max_age_hours=1)
        
        # Phase 1: Fetch stock data
        try:
            stock_data = get_stock_data(symbol, period)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"数据获取失败: {str(e)}", "success": False}), 500
        
        if not stock_data.get('success'):
            return jsonify(stock_data), 400
            
        print(f"[API] Data source: {stock_data.get('source', 'Unknown')}")
        
        # Phase 2: Generate charts
        raw_df = stock_data.pop('raw_df')
        try:
            chart_paths = generate_all_charts(raw_df, symbol)
        except Exception as e:
            traceback.print_exc()
            chart_paths = {}
            print(f"[API] Chart generation failed, continuing without charts: {e}")
        
        # Build chart URLs for frontend
        chart_urls = {}
        for tf, path in chart_paths.items():
            chart_urls[tf] = f"/static/charts/{os.path.basename(path)}"
        
        # Format data for AI
        data_text = format_data_for_ai({**stock_data, 'data': stock_data['data']})
        
        # Phase 3: AI analysis
        try:
            analysis_result = analyze_stock(
                data_text=data_text,
                image_path=chart_paths.get('daily'),
                symbol=symbol,
                model=model,
                image_paths=chart_paths
            )
        except Exception as e:
            traceback.print_exc()
            analysis_result = {"error": f"AI 分析失败: {str(e)}", "success": False}
        
        # Prepare response
        response = {
            "success": True,
            "symbol": symbol,
            "period": period,
            "model": model,
            "chart_url": chart_urls.get('daily', ''),
            "chart_urls": chart_urls,
            "stock_info": stock_data.get('info', {}),
            "indicators": stock_data.get('indicators', {}),
            "stats": stock_data.get('stats', {}),
            "analysis": analysis_result
        }
        
        print(f"[API] ✓ Analysis complete for {symbol}")
        return jsonify(response)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/api/check-keys', methods=['GET'])
def check_keys():
    """Check which API keys are configured"""
    return jsonify({
        "gemini": bool(config.GEMINI_API_KEY),
        "alpha_vantage": bool(config.ALPHA_VANTAGE_API_KEY)
    })


@app.route('/static/charts/<path:filename>')
def serve_chart(filename):
    """Serve chart images"""
    charts_dir = os.path.join(os.path.dirname(__file__), 'static', 'charts')
    return send_from_directory(charts_dir, filename)


if __name__ == '__main__':
    
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        use_reloader=False  # Disable reloader to prevent mid-request server restarts
    )
