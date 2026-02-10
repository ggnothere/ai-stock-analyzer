"""
AI Stock Technical Analyzer - Flask Web Application
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
import os

from stock_data import get_stock_data, format_data_for_ai
from chart_generator import generate_all_charts, cleanup_old_charts
from ai_analyzer import analyze_stock
import config

app = Flask(__name__)

# Ensure charts directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'charts'), exist_ok=True)


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
        
        # Cleanup old charts
        cleanup_old_charts(max_age_hours=1)
        
        # Fetch stock data
        stock_data = get_stock_data(symbol, period)
        
        if not stock_data.get('success'):
            return jsonify(stock_data), 400
        
        # Generate multi-timeframe charts
        raw_df = stock_data.pop('raw_df')  # Remove DataFrame from response
        chart_paths = generate_all_charts(raw_df, symbol)
        
        # Build chart URLs for frontend
        chart_urls = {}
        for tf, path in chart_paths.items():
            chart_urls[tf] = f"/static/charts/{os.path.basename(path)}"
        
        # Format data for AI
        data_text = format_data_for_ai({**stock_data, 'data': stock_data['data']})
        
        # Perform AI analysis with all charts
        analysis_result = analyze_stock(
            data_text=data_text,
            image_path=chart_paths.get('daily'),  # backward compat
            symbol=symbol,
            model=model,
            image_paths=chart_paths
        )
        
        # Prepare response
        response = {
            "success": True,
            "symbol": symbol,
            "period": period,
            "model": model,
            "chart_url": chart_urls.get('daily', ''),  # backward compat
            "chart_urls": chart_urls,
            "stock_info": stock_data.get('info', {}),
            "indicators": stock_data.get('indicators', {}),
            "stats": stock_data.get('stats', {}),
            "analysis": analysis_result
        }
        
        return jsonify(response)
        
    except Exception as e:
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
        port=config.PORT
    )
