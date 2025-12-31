import os
import time
import random
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 模拟的 API Key 配置 (实际使用时应从环境变量获取)
API_KEYS = {
    "deepseek": os.environ.get("DEEPSEEK_API_KEY", "sk-9894b47b4c8642aebaccc6756ccbe490"),
    "chatgpt": os.environ.get("OPENAI_API_KEY", ""),
    "gemini": os.environ.get("GEMINI_API_KEY", ""),
    "doubao": os.environ.get("DOUBAO_API_KEY", "")
}

# 模拟数据生成器


def generate_mock_response(text, context, prompt_type=None):
    if prompt_type == "scholar_profile":
        name = text
        desc = context.get("desc") or context.get("summary") or "这位学者以计算机视觉研究闻名。"
        view_mode = context.get("leaderboardView")
        if view_mode == "nankai":
            return {
                "summary": (
                    f"**{name}** 是南开大学媒体计算团队的中坚力量。\n\n"
                    f"1. **🎓 NKU 使命**：深耕南开计算机视觉方向，{desc}\n"
                    "2. **🧠 核心贡献**：以领先的视觉模型与评价体系，树立 NKU 在国际 CV 社群的辨识度。\n"
                    "3. **🏛️ 阵列气质**：代表了南开视觉研究力量的进取精神，是青年学者的标杆。 (Mock Mode)"
                ),
                "keywords": ["NKU", "Computer Vision", "Media Lab"],
                "confidence": 0.95
            }
        return {
            "summary": f"**{name}** 是 AI 领域的传奇人物。\n\n1. **👑 封神理由**：他是深度学习革命的奠基人之一，图灵奖得主。\n2. **🧠 核心贡献**：{desc}.\n3. **🌟 历史地位**：他在 AI 发展长河中不仅是先驱，更是精神领袖。 (Mock Mode)",
            "keywords": ["Deep Learning", "Turing Award", "AI Safety"],
            "confidence": 0.95
        }
    elif prompt_type == "paper_impact":
        return {
            "summary": f"**《{text}》** 是计算机视觉的里程碑。\n\n1. **💥 破局点**：解决了深度神经网络随着层数增加而无法训练的死胡同。\n2. **🔑 核心魔法**：引入了残差连接（Residual Connection），让梯度可以顺畅流动。\n3. **🌍 世界回响**：成为了所有现代视觉模型的基础组件，引发了深层网络的研究热潮。 (Mock Mode)",
            "keywords": ["ResNet", "Backbone", "Milestone"],
            "confidence": 0.98
        }

    templates = [
        f"关于 '{text}' 的研究在 {context.get('year', '近期')} 表现出显著的增长趋势。",
        f"'{text}' 是计算机视觉领域的核心议题，特别是在 {context.get('venue', '顶级会议')} 上。",
        f"结合上下文分析，'{text}' 通常与 {context.get('related', '深度学习')} 技术结合使用。",
        f"该主题的引用量达到 {context.get('citations', 0)}，显示了其在学术界的高影响力。",
        f"深度解读：'{text}' 代表了 {context.get('year', '当前')} 视觉研究的一个重要分支。"
    ]

    # 随机生成一些关键词
    mock_keywords = ["Computer Vision", "Deep Learning",
                     "AI", "Trend", "Analysis", "Data", "Model"]
    selected_keywords = random.sample(mock_keywords, 3)

    return {
        "summary": random.choice(templates) + " (Mock Mode: 这是一个演示响应，未连接真实 API)",
        "keywords": selected_keywords,
        "confidence": round(random.uniform(0.8, 0.99), 2)
    }

# 模型调用逻辑
# 注意：以下函数在没有真实 API Key 的情况下会返回模拟或错误信息


def call_deepseek(text, context, api_key, prompt_type=None):
    if not api_key:
        # 如果没有 Key，为了演示效果，返回一个带标记的 Mock 数据
        time.sleep(1)
        return generate_mock_response(text, context, prompt_type)

    # 实际调用 DeepSeek API 的代码示例 (需根据官方文档调整)
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}",
                   "Content-Type": "application/json"}

        if prompt_type == "scholar_profile":
            name = text
            desc = context.get("desc", "")
            tags = ", ".join(context.get("concepts", []))
            view_mode = context.get("leaderboardView")
            system_prompt = "你是一个AI名人堂解说员。请用 Markdown 格式回答，语气专业且带有崇敬感。"
            if view_mode == "nankai":
                user_content = (
                    f"请介绍南开大学计算机视觉领域的杰出学者 {name}。\n"
                    f"他/她在南开大学媒体计算团队（NKU Media Lab）中扮演着重要角色。\n"
                    f"请重点解读其在 CV 领域的核心学术地位，以及对他/她所代表的南开视觉研究力量的评价。"
                )
            else:
                user_content = (
                    f"请介绍计算机科学家 {name}。\n"
                    f"背景信息：{desc}\n"
                    f"请用 Markdown 格式回答：\n"
                    f"1. **👑 封神理由**：一句话概括他为什么是 Top 级别。\n"
                    f"2. **🧠 核心贡献**：通俗解释他的 1-2 个代表作（如 {tags}）。\n"
                    f"3. **🌟 历史地位**：他在 AI 发展长河中的坐标。\n"
                    f"字数 250 字以内，保持简洁有力。"
                )
        elif prompt_type == "paper_impact":
            title = text
            system_prompt = "你是一个技术史学家。请用 Markdown 格式解读经典论文。"
            user_content = (
                f"经典论文《{title}》是引用量极高的镇山之作。\n"
                f"请以【技术史学家】的视角解读：\n"
                f"1. **💥 破局点**：在它出现之前，领域面临什么死胡同？\n"
                f"2. **🔑 核心魔法**：它用什么简单的直觉解决了问题？\n"
                f"3. **🌍 世界回响**：它如何影响了后来的研究？\n"
                f"字数 250 字以内，使用 Markdown 列表格式，保持简洁。"
            )
        else:
            system_prompt = "你是一个专业的计算机视觉研究助手。请直接输出分析内容，不要包含'好的'、'以下是分析'等客套话。**回答必须非常简明扼要，严格控制篇幅，只列出最核心的定义、关键技术点和趋势，避免任何冗余解释。**请使用 Markdown 格式。对于数学公式，请使用 LaTeX 格式，行内公式用 \\( ... \\) 包裹，独立公式用 \\[ ... \\] 包裹。"
            user_content = f"请简要分析计算机视觉中的概念: {text}。上下文信息: {json.dumps(context)}"

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 1024
        }
        response = requests.post(url, headers=headers,
                                 json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return {"summary": content, "keywords": ["DeepSeek-API"], "confidence": 1.0}
    except Exception as e:
        return {"error": f"DeepSeek API 调用失败: {str(e)}"}


def call_chatgpt(text, context, api_key):
    if not api_key:
        time.sleep(1)
        return {
            "summary": f"[ChatGPT 模式] (未配置 API Key) 作为 AI 语言模型，我认为 '{text}' 是个有趣的话题。",
            "keywords": ["OpenAI", "GPT-4", "NLP"],
            "confidence": 0.0
        }
    # 实际调用 OpenAI API 的代码示例
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}",
                   "Content-Type": "application/json"}

        system_prompt = "你是一个专业的计算机视觉研究助手。请直接输出分析内容，不要包含任何客套话。**回答必须非常简明扼要，严格控制篇幅，只列出最核心的定义、关键技术点和趋势，避免任何冗余解释。**请使用 Markdown 格式。对于数学公式，请使用 LaTeX 格式，行内公式用 \\( ... \\) 包裹，独立公式用 \\[ ... \\] 包裹。"

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"分析 CV 论文主题: {text}。背景: {context}"}
            ],
            "max_tokens": 1024
        }
        response = requests.post(url, headers=headers,
                                 json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return {"summary": content, "keywords": ["GPT-API"], "confidence": 1.0}
    except Exception as e:
        return {"error": f"OpenAI API 调用失败: {str(e)}"}


def call_gemini(text, context, api_key):
    if not api_key:
        time.sleep(1)
        return {
            "summary": f"[Gemini 模式] (未配置 API Key) Google 的多模态模型正在分析 '{text}' 的视觉与文本关联。",
            "keywords": ["Gemini", "Google", "Multimodal"],
            "confidence": 0.0
        }
    # TODO: 实现 Gemini API 调用
    return {"summary": "Gemini API 暂未实现", "keywords": [], "confidence": 0.0}


def call_doubao(text, context, api_key):
    if not api_key:
        time.sleep(1)
        return {
            "summary": f"[豆包模式] (未配置 API Key) 字节跳动豆包大模型为您解读 '{text}'。",
            "keywords": ["Doubao", "ByteDance", "Chinese"],
            "confidence": 0.0
        }
    # TODO: 实现 Doubao API 调用
    return {"summary": "Doubao API 暂未实现", "keywords": [], "confidence": 0.0}


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400

        text = data.get('text', '')
        context = data.get('context', {})
        model = data.get('model', 'mock')
        prompt_type = data.get('prompt_type')

        # 优先使用前端传入的 API Key，否则使用环境变量配置的
        request_api_key = data.get('api_key', '')
        api_key = request_api_key if request_api_key else API_KEYS.get(
            model, "")

        print(
            f"[{time.strftime('%H:%M:%S')}] 收到分析请求: Model={model}, Type={prompt_type}, Text={text[:20]}...")

        if model == 'mock':
            time.sleep(0.8)  # 模拟网络延迟
            result = generate_mock_response(text, context, prompt_type)
        elif model == 'deepseek':
            result = call_deepseek(text, context, api_key, prompt_type)
        elif model == 'chatgpt':
            result = call_chatgpt(text, context, api_key)
        elif model == 'gemini':
            result = call_gemini(text, context, api_key)
        elif model == 'doubao':
            result = call_doubao(text, context, api_key)
        else:
            return jsonify({"error": f"不支持的模型: {model}"}), 400

        # 如果结果中有错误信息
        if "error" in result:
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        print(f"服务器内部错误: {e}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "models": list(API_KEYS.keys()) + ['mock'],
        "version": "1.0.0"
    })


if __name__ == '__main__':
    print("="*40)
    print("CV Explorer Backend Server Running")
    print("Address: http://localhost:5000")
    print("Supported Models: Mock, DeepSeek, ChatGPT, Gemini, Doubao")
    print("="*40)
    app.run(host='0.0.0.0', port=5000, debug=True)
