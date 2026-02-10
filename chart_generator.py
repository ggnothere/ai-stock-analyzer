"""
AI Stock Technical Analyzer - Chart Generator
Uses mplfinance to generate professional candlestick charts
Supports daily, weekly, and monthly timeframes
"""
import matplotlib
matplotlib.use('Agg')  # Must be before mplfinance import - avoids tkinter crash in Flask
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import os
from datetime import datetime


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV data to weekly"""
    weekly = df.resample('W').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum',
    }).dropna()
    
    # Recalculate indicators for weekly
    if len(weekly) >= 20:
        weekly['MA_20'] = weekly['Close'].rolling(window=20).mean()
    if len(weekly) >= 50:
        weekly['MA_50'] = weekly['Close'].rolling(window=50).mean()
    
    return weekly


def resample_to_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV data to monthly"""
    monthly = df.resample('ME').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum',
    }).dropna()
    
    # Recalculate indicators for monthly
    if len(monthly) >= 12:
        monthly['MA_20'] = monthly['Close'].rolling(window=12).mean()
    
    return monthly


def _generate_single_chart(chart_df: pd.DataFrame, symbol: str, 
                           timeframe: str, filepath: str, 
                           show_days: int = 60) -> str:
    """
    Generate a single candlestick chart for a given timeframe
    
    Args:
        chart_df: DataFrame with OHLCV data
        symbol: Stock ticker symbol
        timeframe: 'daily', 'weekly', or 'monthly'
        filepath: Path to save the chart
        show_days: Number of bars to show
    
    Returns:
        Path to the saved chart image
    """
    # Ensure DatetimeIndex
    if not isinstance(chart_df.index, pd.DatetimeIndex):
        if 'Date' in chart_df.columns:
            chart_df['Date'] = pd.to_datetime(chart_df['Date'])
            chart_df.set_index('Date', inplace=True)
    
    # Limit bars to show
    chart_df = chart_df.tail(show_days)
    
    if len(chart_df) < 5:
        return None  # Not enough data
    
    # Timeframe labels
    tf_labels = {
        'daily': '日K线',
        'weekly': '周K线', 
        'monthly': '月K线'
    }
    tf_label = tf_labels.get(timeframe, timeframe)
    
    # Detect currency
    price = chart_df['Close'].iloc[-1]
    currency_label = 'Price (¥)' if price > 5 and symbol[0].isdigit() else 'Price ($)'
    
    # Define custom style (dark theme)
    mc = mpf.make_marketcolors(
        up='#00ff88',      # Green for up
        down='#ff4444',    # Red for down
        edge='inherit',
        wick='inherit',
        volume='inherit',
    )
    
    s = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        marketcolors=mc,
        gridstyle='-',
        gridcolor='#333333',
        facecolor='#1a1a2e',
        figcolor='#1a1a2e',
        rc={'font.size': 10}
    )
    
    # Prepare additional plots
    add_plots = []
    
    # Moving averages
    if 'MA_20' in chart_df.columns and not chart_df['MA_20'].isna().all():
        ma20_label = 'MA20' if timeframe == 'daily' else ('MA20W' if timeframe == 'weekly' else 'MA12M')
        add_plots.append(mpf.make_addplot(chart_df['MA_20'], color='#ffd700', width=1, label=ma20_label))
    if 'MA_50' in chart_df.columns and not chart_df['MA_50'].isna().all():
        add_plots.append(mpf.make_addplot(chart_df['MA_50'], color='#ff69b4', width=1, label='MA50'))
    
    # Bollinger Bands (daily only)
    if timeframe == 'daily':
        if 'BB_Upper' in chart_df.columns and not chart_df['BB_Upper'].isna().all():
            add_plots.append(mpf.make_addplot(chart_df['BB_Upper'], color='#4a90d9', width=0.7, linestyle='--'))
            add_plots.append(mpf.make_addplot(chart_df['BB_Lower'], color='#4a90d9', width=0.7, linestyle='--'))
        
        # RSI subplot (daily only)
        if 'RSI_14' in chart_df.columns and not chart_df['RSI_14'].isna().all():
            add_plots.append(mpf.make_addplot(chart_df['RSI_14'], panel=2, color='#00bfff', width=1, ylabel='RSI'))
            rsi_70 = pd.Series([70] * len(chart_df), index=chart_df.index)
            rsi_30 = pd.Series([30] * len(chart_df), index=chart_df.index)
            add_plots.append(mpf.make_addplot(rsi_70, panel=2, color='#ff6666', width=0.5, linestyle='--'))
            add_plots.append(mpf.make_addplot(rsi_30, panel=2, color='#66ff66', width=0.5, linestyle='--'))
        
        # MACD subplot (daily only)
        if 'MACD' in chart_df.columns and not chart_df['MACD'].isna().all():
            add_plots.append(mpf.make_addplot(chart_df['MACD'], panel=3, color='#00ff88', width=1, ylabel='MACD'))
            add_plots.append(mpf.make_addplot(chart_df['MACD_Signal'], panel=3, color='#ff69b4', width=1))
            hist_colors = ['#00ff88' if v >= 0 else '#ff4444' for v in chart_df['MACD_Hist'].fillna(0)]
            add_plots.append(mpf.make_addplot(chart_df['MACD_Hist'], panel=3, type='bar', color=hist_colors, width=0.7))
    
    # Determine panel ratios
    has_rsi = timeframe == 'daily' and 'RSI_14' in chart_df.columns and not chart_df['RSI_14'].isna().all()
    has_macd = timeframe == 'daily' and 'MACD' in chart_df.columns and not chart_df['MACD'].isna().all()
    
    if has_rsi and has_macd:
        panel_ratios = (4, 1, 1, 1)
    elif has_rsi or has_macd:
        panel_ratios = (4, 1, 1)
    else:
        panel_ratios = (3, 1)
    
    # Chart size: daily is larger, weekly/monthly smaller
    figsize = (14, 10) if timeframe == 'daily' else (14, 7)
    
    # Generate chart
    fig, axes = mpf.plot(
        chart_df,
        type='candle',
        style=s,
        title=f'\n{symbol.upper()} {tf_label}',
        ylabel=currency_label,
        volume=True,
        volume_panel=1,
        addplot=add_plots if add_plots else None,
        figsize=figsize,
        panel_ratios=panel_ratios,
        returnfig=True,
        tight_layout=True,
    )
    
    # Save chart
    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close(fig)
    
    return filepath


def generate_all_charts(df: pd.DataFrame, symbol: str) -> dict:
    """
    Generate daily, weekly, and monthly charts
    
    Args:
        df: DataFrame with OHLCV data and indicators (daily)
        symbol: Stock ticker symbol
    
    Returns:
        Dictionary with chart paths: {'daily': path, 'weekly': path, 'monthly': path}
    """
    charts_dir = os.path.join(os.path.dirname(__file__), 'static', 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_paths = {}
    
    # Daily chart (last 60 bars)
    daily_path = os.path.join(charts_dir, f"{symbol.upper()}_{timestamp}_daily.png")
    result = _generate_single_chart(df.copy(), symbol, 'daily', daily_path, show_days=60)
    if result:
        chart_paths['daily'] = result
        print(f"[Chart] ✓ Daily chart generated")
    
    # Weekly chart (last 52 weeks)
    try:
        weekly_df = resample_to_weekly(df[['Open', 'High', 'Low', 'Close', 'Volume']].copy())
        if len(weekly_df) >= 10:
            weekly_path = os.path.join(charts_dir, f"{symbol.upper()}_{timestamp}_weekly.png")
            result = _generate_single_chart(weekly_df, symbol, 'weekly', weekly_path, show_days=52)
            if result:
                chart_paths['weekly'] = result
                print(f"[Chart] ✓ Weekly chart generated")
    except Exception as e:
        print(f"[Chart] ✗ Weekly chart error: {e}")
    
    # Monthly chart (last 24 months)
    try:
        monthly_df = resample_to_monthly(df[['Open', 'High', 'Low', 'Close', 'Volume']].copy())
        if len(monthly_df) >= 6:
            monthly_path = os.path.join(charts_dir, f"{symbol.upper()}_{timestamp}_monthly.png")
            result = _generate_single_chart(monthly_df, symbol, 'monthly', monthly_path, show_days=24)
            if result:
                chart_paths['monthly'] = result
                print(f"[Chart] ✓ Monthly chart generated")
    except Exception as e:
        print(f"[Chart] ✗ Monthly chart error: {e}")
    
    return chart_paths


def generate_chart(df: pd.DataFrame, symbol: str, save_path: str = None) -> str:
    """
    Generate a daily candlestick chart (backward compatibility)
    
    Returns:
        Path to the saved chart image
    """
    charts_dir = os.path.join(os.path.dirname(__file__), 'static', 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{symbol.upper()}_{timestamp}.png"
    filepath = save_path or os.path.join(charts_dir, filename)
    
    result = _generate_single_chart(df.copy(), symbol, 'daily', filepath, show_days=60)
    return result or filepath


def get_chart_url(symbol: str) -> str:
    """Get the URL path for a chart"""
    charts_dir = os.path.join(os.path.dirname(__file__), 'static', 'charts')
    
    # Find the most recent chart for this symbol
    if os.path.exists(charts_dir):
        files = [f for f in os.listdir(charts_dir) if f.startswith(symbol.upper())]
        if files:
            files.sort(reverse=True)
            return f"/static/charts/{files[0]}"
    
    return None


def cleanup_old_charts(max_age_hours: int = 24):
    """Remove charts older than specified hours"""
    import time
    
    charts_dir = os.path.join(os.path.dirname(__file__), 'static', 'charts')
    if not os.path.exists(charts_dir):
        return
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for filename in os.listdir(charts_dir):
        filepath = os.path.join(charts_dir, filename)
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > max_age_seconds:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
