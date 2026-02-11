"""
AI Stock Technical Analyzer - Stock Data Module
Supports Alpha Vantage (primary) and yfinance (fallback)
"""
import requests
import pandas as pd
import numpy as np
import math
import time
from datetime import datetime, timedelta
import config


def _request_with_retry(url, params=None, timeout=15, max_retries=2):
    """HTTP GET with retry logic for transient network errors"""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError) as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt  # 1s, 2s
                print(f"[Network] Retry {attempt+1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
    raise last_error


def safe_value(val, decimal_places=2):
    """Convert NaN/Inf to None for JSON serialization"""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return None
    try:
        return round(float(val), decimal_places)
    except (TypeError, ValueError):
        return None


import re


def is_a_share(symbol: str) -> bool:
    """Detect if the symbol is a Chinese A-share stock"""
    symbol = symbol.upper().strip()
    # Patterns: 600xxx, 601xxx, 603xxx (Shanghai), 000xxx, 001xxx, 002xxx, 300xxx, 301xxx (Shenzhen)
    # Or with suffix: 600519.SS, 600519.SH, 000858.SZ
    if re.match(r'^(6\d{5}|0\d{5}|3\d{5})(\.(SS|SH|SZ|SHH|SHZ))?$', symbol):
        return True
    # Also match Chinese exchange suffix
    if symbol.endswith(('.SS', '.SH', '.SZ', '.SHH', '.SHZ')):
        return True
    return False


def get_pure_code(symbol: str) -> str:
    """Extract pure 6-digit stock code from symbol"""
    return re.sub(r'\.(SS|SH|SZ|SHH|SHZ)$', '', symbol.upper().strip())


def get_stock_data(symbol: str, period: str = "2y") -> dict:
    """
    Fetch stock data and calculate technical indicators
    Auto-detects A-share vs US stock and uses appropriate data source
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL' for US, '600519' for A-share)
        period: Data period ('1mo', '3mo', '6mo', '1y', '2y')
    
    Returns:
        Dictionary containing stock info and OHLCV data with indicators
    """
    # Detect A-share and use AKShare
    if is_a_share(symbol):
        print(f"[Data] Detected A-share: {symbol}, using AKShare...")
        result = get_data_akshare(symbol, period)
        if result.get("success"):
            return result
        print(f"[Data] AKShare failed: {result.get('error')}, trying yfinance...")
        # Fallback to yfinance with .SS/.SZ suffix
        code = get_pure_code(symbol)
        yf_symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
        return get_data_yfinance(yf_symbol, period)
    
    # US stocks: try Alpha Vantage first
    if config.ALPHA_VANTAGE_API_KEY:
        print(f"[Data] Fetching {symbol} from Alpha Vantage...")
        result = get_data_alpha_vantage(symbol, period)
        if result.get("success"):
            return result
        print(f"[Data] Alpha Vantage failed: {result.get('error')}, trying yfinance...")
    
    # Fallback to yfinance
    print(f"[Data] Fetching {symbol} from yfinance...")
    return get_data_yfinance(symbol, period)


def get_data_akshare(symbol: str, period: str = "2y") -> dict:
    """Fetch A-share stock data from AKShare"""
    try:
        import akshare as ak
        
        code = get_pure_code(symbol)
        
        # Calculate start date based on period
        period_days = {
            "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "5y": 1825, "max": 3650
        }
        days = period_days.get(period, 730)
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')
        
        # Fetch daily data
        print(f"[AKShare] Fetching {code} from {start_date} to {end_date}...")
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df is None or df.empty:
            return {"error": f"AKShare: No data found for {code}", "success": False}
        
        # Rename columns to standard format
        column_map = {
            '日期': 'Date',
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume',
        }
        df = df.rename(columns=column_map)
        
        # Ensure required columns exist
        required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        for col in required:
            if col not in df.columns:
                return {"error": f"AKShare: Missing column {col}", "success": False}
        
        # Set Date as index
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # Convert to float
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col].astype(float)
        df['Volume'] = df['Volume'].astype(int)
        
        # Get stock info
        stock_info = get_stock_info_akshare(code, df)
        
        # Calculate technical indicators
        df = calculate_indicators(df)
        
        # Prepare data for JSON
        df_json = df.reset_index()
        df_json['Date'] = df_json['Date'].dt.strftime('%Y-%m-%d')
        df_json = df_json.replace({np.nan: None})
        
        # Get latest indicator values
        latest = df.iloc[-1]
        indicators = build_indicators(latest)
        stats = build_stats(df)
        
        print(f"[Data] ✓ Got {len(df)} days of A-share data for {code} from AKShare")
        
        return {
            "success": True,
            "info": stock_info,
            "indicators": indicators,
            "stats": stats,
            "data": df_json.to_dict(orient='records'),
            "raw_df": df
        }
        
    except Exception as e:
        return {"error": f"AKShare error: {str(e)}", "success": False}


def get_stock_info_akshare(code: str, df: pd.DataFrame) -> dict:
    """Get A-share stock info from AKShare"""
    try:
        import akshare as ak
        info_df = ak.stock_individual_info_em(symbol=code)
        
        # Parse info into dict
        info = {}
        if info_df is not None and not info_df.empty:
            for _, row in info_df.iterrows():
                info[row.iloc[0]] = row.iloc[1]
        
        return {
            "symbol": code,
            "name": info.get("股票简称", code),
            "currency": "CNY",
            "exchange": "上交所" if code.startswith('6') else "深交所",
            "sector": info.get("行业", ""),
            "industry": info.get("行业", ""),
            "marketCap": int(float(info.get("总市值", 0) or 0)),
            "currentPrice": round(df['Close'].iloc[-1], 2) if not df.empty else 0,
        }
    except Exception:
        return {
            "symbol": code,
            "name": code,
            "currency": "CNY",
            "exchange": "上交所" if code.startswith('6') else "深交所",
            "sector": "",
            "industry": "",
            "marketCap": 0,
            "currentPrice": round(df['Close'].iloc[-1], 2) if not df.empty else 0,
        }


def get_data_alpha_vantage(symbol: str, period: str = "2y") -> dict:
    """Fetch stock data from Alpha Vantage API"""
    try:
        api_key = config.ALPHA_VANTAGE_API_KEY
        
        # Determine output size based on period
        period_days = {
            "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "5y": 1825, "max": 9999
        }
        days_needed = period_days.get(period, 730)
        outputsize = "full" if days_needed > 100 else "compact"
        
        # Fetch daily data
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol.upper(),
            "outputsize": outputsize,
            "apikey": api_key
        }
        
        response = _request_with_retry(url, params=params, timeout=15)
        data = response.json()
        
        # Check for errors
        if "Error Message" in data:
            return {"error": f"Alpha Vantage: {data['Error Message']}", "success": False}
        if "Note" in data:
            return {"error": f"Alpha Vantage API limit reached: {data['Note']}", "success": False}
        if "Information" in data:
            return {"error": f"Alpha Vantage: {data['Information']}", "success": False}
        
        time_series = data.get("Time Series (Daily)", {})
        if not time_series:
            return {"error": f"No data found for {symbol}", "success": False}
        
        # Convert to DataFrame
        records = []
        for date_str, values in time_series.items():
            records.append({
                "Date": pd.Timestamp(date_str),
                "Open": float(values["1. open"]),
                "High": float(values["2. high"]),
                "Low": float(values["3. low"]),
                "Close": float(values["4. close"]),
                "Volume": int(values["5. volume"])
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values("Date").reset_index(drop=True)
        df.set_index("Date", inplace=True)
        
        # Filter to requested period
        cutoff_date = datetime.now() - timedelta(days=days_needed)
        df = df[df.index >= pd.Timestamp(cutoff_date)]
        
        if df.empty:
            return {"error": f"No data found for {symbol} in period {period}", "success": False}
        
        # Get stock info from Alpha Vantage overview
        stock_info = get_stock_info_av(symbol, api_key, df)
        
        # Calculate technical indicators
        df = calculate_indicators(df)
        
        # Prepare data for JSON
        df_json = df.reset_index()
        df_json['Date'] = df_json['Date'].dt.strftime('%Y-%m-%d')
        df_json = df_json.replace({np.nan: None})
        
        # Get latest indicator values
        latest = df.iloc[-1]
        indicators = build_indicators(latest)
        
        # Price statistics
        stats = build_stats(df)
        
        print(f"[Data] ✓ Got {len(df)} days of data for {symbol} from Alpha Vantage")
        
        return {
            "success": True,
            "info": stock_info,
            "indicators": indicators,
            "stats": stats,
            "data": df_json.to_dict(orient='records'),
            "raw_df": df
        }
        
    except Exception as e:
        return {"error": str(e), "success": False}


def get_stock_info_av(symbol: str, api_key: str, df: pd.DataFrame) -> dict:
    """Get stock info from Alpha Vantage OVERVIEW endpoint"""
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": api_key
        }
        response = _request_with_retry(url, params=params, timeout=10, max_retries=1)
        info = response.json()
        
        return {
            "symbol": symbol.upper(),
            "name": info.get("Name", symbol),
            "currency": info.get("Currency", "USD"),
            "exchange": info.get("Exchange", ""),
            "sector": info.get("Sector", ""),
            "industry": info.get("Industry", ""),
            "marketCap": int(info.get("MarketCapitalization", 0) or 0),
            "currentPrice": round(df['Close'].iloc[-1], 2) if not df.empty else 0,
        }
    except Exception:
        return {
            "symbol": symbol.upper(),
            "name": symbol,
            "currency": "USD",
            "exchange": "",
            "sector": "",
            "industry": "",
            "marketCap": 0,
            "currentPrice": round(df['Close'].iloc[-1], 2) if not df.empty else 0,
        }


def get_data_yfinance(symbol: str, period: str = "2y") -> dict:
    """Fetch stock data from yfinance (fallback)"""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        
        if df.empty:
            return {"error": f"No data found for {symbol}", "success": False}
        
        # Get stock info (protected - stock.info can crash)
        try:
            info = stock.info or {}
        except Exception:
            info = {}
        stock_info = {
            "symbol": symbol.upper(),
            "name": info.get("longName", symbol),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "marketCap": info.get("marketCap", 0),
            "currentPrice": info.get("currentPrice", df['Close'].iloc[-1] if not df.empty else 0),
        }
        
        # Calculate technical indicators
        df = calculate_indicators(df)
        
        # Prepare data for JSON
        df_json = df.reset_index()
        if df_json['Date'].dt.tz is not None:
            df_json['Date'] = df_json['Date'].dt.tz_localize(None)
        df_json['Date'] = df_json['Date'].dt.strftime('%Y-%m-%d')
        df_json = df_json.replace({np.nan: None})
        
        # Get latest indicator values
        latest = df.iloc[-1]
        indicators = build_indicators(latest)
        stats = build_stats(df)
        
        print(f"[Data] ✓ Got {len(df)} days of data for {symbol} from yfinance")
        
        return {
            "success": True,
            "info": stock_info,
            "indicators": indicators,
            "stats": stats,
            "data": df_json.to_dict(orient='records'),
            "raw_df": df
        }
        
    except Exception as e:
        return {"error": str(e), "success": False}


def build_indicators(latest) -> dict:
    """Build indicators dict from latest row, handling NaN"""
    return {
        "rsi_14": safe_value(latest.get('RSI_14')),
        "ma_20": safe_value(latest.get('MA_20')),
        "ma_50": safe_value(latest.get('MA_50')),
        "ma_200": safe_value(latest.get('MA_200')),
        "macd": safe_value(latest.get('MACD'), 4),
        "macd_signal": safe_value(latest.get('MACD_Signal'), 4),
        "macd_hist": safe_value(latest.get('MACD_Hist'), 4),
        "bb_upper": safe_value(latest.get('BB_Upper')),
        "bb_middle": safe_value(latest.get('BB_Middle')),
        "bb_lower": safe_value(latest.get('BB_Lower')),
        "atr_14": safe_value(latest.get('ATR_14')),
    }


def build_stats(df) -> dict:
    """Build price statistics dict"""
    return {
        "period_high": round(df['High'].max(), 2),
        "period_low": round(df['Low'].min(), 2),
        "period_change": round((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100, 2),
        "avg_volume": int(df['Volume'].mean()),
        "latest_close": round(df['Close'].iloc[-1], 2),
        "latest_volume": int(df['Volume'].iloc[-1]),
    }


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators"""
    
    # Data validation: drop rows with invalid OHLCV
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    df = df[df['Close'] > 0]  # Remove zero/negative prices
    
    if df.empty:
        return df
    
    # Moving Averages
    df['MA_20'] = df['Close'].rolling(window=20).mean()
    df['MA_50'] = df['Close'].rolling(window=50).mean()
    df['MA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI
    df['RSI_14'] = calculate_rsi(df['Close'], 14)
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # ATR
    df['ATR_14'] = calculate_atr(df, 14)
    
    return df


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def format_data_for_ai(stock_data: dict) -> str:
    """Format stock data as text for AI analysis"""
    if not stock_data.get("success"):
        return f"Error: {stock_data.get('error', 'Unknown error')}"
    
    info = stock_data["info"]
    indicators = stock_data["indicators"]
    stats = stock_data["stats"]
    
    # Get recent price data (last 20 days)
    recent_data = stock_data["data"][-20:]
    
    text = f"""
股票信息：
- 代码：{info['symbol']}
- 名称：{info['name']}
- 行业：{info.get('sector', 'N/A')} - {info.get('industry', 'N/A')}
- 当前价格：${stats['latest_close']}

价格统计（分析周期内）：
- 最高价：${stats['period_high']}
- 最低价：${stats['period_low']}
- 区间涨跌幅：{stats['period_change']}%
- 日均成交量：{stats['avg_volume']:,}

技术指标（最新值）：
- RSI(14)：{indicators['rsi_14']}
- MA20：${indicators['ma_20']}
- MA50：${indicators['ma_50']}
- MA200：${indicators['ma_200'] if indicators['ma_200'] is not None else 'N/A'}
- MACD：{indicators['macd']}
- MACD Signal：{indicators['macd_signal']}
- MACD Histogram：{indicators['macd_hist']}
- 布林带上轨：${indicators['bb_upper']}
- 布林带中轨：${indicators['bb_middle']}
- 布林带下轨：${indicators['bb_lower']}
- ATR(14)：${indicators['atr_14']}

最近20个交易日数据：
日期 | 开盘 | 最高 | 最低 | 收盘 | 成交量
"""
    
    for day in recent_data:
        try:
            o = f"${day['Open']:.2f}" if day.get('Open') is not None else "N/A"
            h = f"${day['High']:.2f}" if day.get('High') is not None else "N/A"
            l = f"${day['Low']:.2f}" if day.get('Low') is not None else "N/A"
            c = f"${day['Close']:.2f}" if day.get('Close') is not None else "N/A"
            v = f"{int(day['Volume']):,}" if day.get('Volume') is not None else "N/A"
            text += f"{day['Date']} | {o} | {h} | {l} | {c} | {v}\n"
        except (TypeError, ValueError):
            continue
    
    return text
