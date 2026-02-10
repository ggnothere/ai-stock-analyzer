"""
AI Stock Technical Analyzer - AI Analysis Module
Supports both Gemini and ChatGPT APIs for stock analysis
"""
import os
import base64
import traceback
from typing import Optional
import config


def encode_image(image_path: str) -> str:
    """Encode image to base64 for API submission"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_analysis_prompt(symbol: str, data_text: str) -> str:
    """Generate the analysis prompt for AI"""
    return f"""请对以下美股进行全面的技术分析：

{data_text}

请从以下维度进行深入分析：

## 1. 趋势分析
- 短期趋势（1-2周）
- 中期趋势（1-3个月）
- 长期趋势（6个月以上）
- 当前所处趋势阶段

## 2. 关键价位
- 重要支撑位（至少2-3个）
- 重要阻力位（至少2-3个）
- 支撑/阻力强度评估

## 3. 技术指标解读
- RSI 分析（超买/超卖/背离）
- MACD 分析（金叉/死叉/动能）
- 均线系统分析（多头/空头排列、均线粘合/发散）
- 布林带分析（收口/张口、突破信号）

## 4. 成交量分析
- 量价配合情况
- 是否有异常放量/缩量
- 成交量趋势

## 5. 形态识别
- 是否存在经典形态（头肩、双顶/底、三角形等）
- 形态完成度评估

## 6. 综合评估
- 多空力量对比
- 当前风险评估（1-10分，10为最高风险）
- 机会评估（1-10分，10为最佳机会）

## 7. 操作建议
- 短线操作建议
- 中线操作建议
- 建议仓位配置
- 止损位建议
- 目标价位

请用中文详细回答，给出具体的价格点位。分析要专业、客观，既要指出机会也要提示风险。"""


def analyze_with_gemini(data_text: str, image_path: Optional[str] = None, 
                        symbol: str = "", model_name: str = "gemini-3-flash-preview",
                        image_paths: Optional[dict] = None) -> dict:
    """
    Analyze stock using Google Gemini API
    
    Args:
        data_text: Formatted stock data text
        image_path: Path to single chart image (backward compat)
        symbol: Stock symbol
        model_name: Gemini model to use
        image_paths: Dict of {'daily': path, 'weekly': path, 'monthly': path}
    
    Returns:
        Dictionary with analysis result
    """
    try:
        import google.generativeai as genai
        
        api_key = config.GEMINI_API_KEY
        if not api_key:
            return {"error": "Gemini API key not configured", "success": False}
        
        print(f"[Gemini] Configuring API with model: {model_name}")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(model_name)
        prompt = get_analysis_prompt(symbol, data_text)
        
        # Prepare content with multiple images
        content = []
        images_added = 0
        
        if image_paths:
            tf_labels = {'daily': '日K线图', 'weekly': '周K线图', 'monthly': '月K线图'}
            content.append("请结合以下多维度K线图（日线、周线、月线）和技术数据，从多个时间维度进行全面分析：\n\n")
            
            for tf in ['daily', 'weekly', 'monthly']:
                path = image_paths.get(tf)
                if path and os.path.exists(path):
                    import PIL.Image
                    image = PIL.Image.open(path)
                    content.append(f"\n【{tf_labels.get(tf, tf)}】\n")
                    content.append(image)
                    images_added += 1
                    print(f"[Gemini] Including {tf} chart: {path}")
            
            content.append("\n\n" + prompt)
        elif image_path and os.path.exists(image_path):
            import PIL.Image
            image = PIL.Image.open(image_path)
            content = ["请结合以下K线图和数据进行分析：\n\n" + prompt, image]
            images_added = 1
            print(f"[Gemini] Including chart image: {image_path}")
        else:
            content = [prompt]
        
        print(f"[Gemini] Sending request to {model_name} with {images_added} chart(s)...")
        response = model.generate_content(
            content,
            request_options={"timeout": 120}
        )
        
        display_name = "Gemini 3 Flash" if "flash" in model_name else "Gemini 3 Pro"
        
        print(f"[Gemini] ✓ Analysis complete ({display_name})")
        return {
            "success": True,
            "analysis": response.text,
            "model": display_name
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[Gemini] ✗ Error: {error_msg}")
        traceback.print_exc()
        return {"error": error_msg, "success": False}


def analyze_stock(data_text: str, image_path: Optional[str] = None, 
                  symbol: str = "", model: str = "gemini-flash",
                  image_paths: Optional[dict] = None) -> dict:
    """
    Main function to analyze stock with selected Gemini model
    
    Args:
        data_text: Formatted stock data
        image_path: Path to chart image (single, backward compat)
        symbol: Stock symbol
        model: 'gemini-flash' or 'gemini-pro'
        image_paths: Dict of timeframe chart paths
    
    Returns:
        Analysis result dictionary
    """
    if model.lower() in ["gemini", "gemini-flash"]:
        return analyze_with_gemini(data_text, image_path, symbol, "gemini-3-flash-preview", image_paths)
    elif model.lower() == "gemini-pro":
        return analyze_with_gemini(data_text, image_path, symbol, "gemini-3-pro-preview", image_paths)
    else:
        return analyze_with_gemini(data_text, image_path, symbol, "gemini-3-flash-preview", image_paths)
