"""AI同士の会話システム設定"""

import json

# LMStudio API設定
API_BASE_URL = "http://127.0.0.1:1234/v1"
API_KEY = "lm-studio"

# 会話設定
MAX_TURNS = 20  # 各AIの最大発言回数

# ファイルパス
CONFIG_FILE = "/tmp/ai_conversation_config.json"
CHAR_FILE = "/tmp/ai_conversation_chars.json"


def load_user_config() -> dict:
    """ユーザーが入力した設定を読み込む"""
    default = {
        "model": "default",
        "role": "友人同士",
        "topic": "最近あった面白いこと",
    }
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return {**default, **config}
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_characters() -> dict:
    """LLMで生成されたキャラクター情報を読み込む"""
    try:
        with open(CHAR_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_speech_style_instruction(formality: str, speech_example: str) -> str:
    """敬語レベルに応じた話し方の指示を生成"""
    if formality == "casual":
        base = "タメ口で話す（「です」「ます」は使わない）"
    elif formality == "respectful":
        base = "敬語（です・ます調）で話す"
    else:  # polite
        base = "丁寧語（です・ます調）で話す"

    return f"{base}\n- 例: {speech_example}"


def create_system_prompt(char: dict, partner_name: str, relation: str, topic: str) -> str:
    """キャラクター情報からシステムプロンプトを生成"""

    formality = char.get("formality", "polite")
    speech_example = char.get("speech_example", "")

    # 敬語に関する強調指示
    if formality == "casual":
        formality_instruction = "【重要】タメ口で話してください。「です」「ます」は絶対に使わないでください。"
    elif formality == "respectful":
        formality_instruction = "【重要】敬語（です・ます調）で話してください。タメ口は絶対に使わないでください。"
    else:
        formality_instruction = "【重要】丁寧語（です・ます調）で話してください。"

    return f"""あなたは「{char['name']}」という名前の{char['age']}歳です。
あなたの役割: {char['role_description']}
関係性: {partner_name}との関係は「{relation}」です。

今日の話題: {topic}

【話し方】
{get_speech_style_instruction(formality, speech_example)}
- 一人称は「{char['pronoun']}」を使う

{formality_instruction}

【注意事項】
- 自然な会話を心がける
- 長すぎない返答（2-4文程度）
- 話題に沿って会話する（脱線してもOK）
- <think>タグや/no_thinkを出力に含めない
- 会話が自然に終わりそうなら別れの挨拶で締める（無理に続けない）"""


# 会話終了検知用キーワード
FAREWELL_KEYWORDS = [
    "またね", "じゃあね", "バイバイ", "お元気で", "また今度",
    "じゃーね", "またよろしく", "お大事に", "気をつけて",
    "また連絡", "また話そう", "楽しみにしてる", "またな",
    "失礼します", "失礼いたします", "ありがとうございました",
    "お疲れ様", "それでは", "では、", "ではまた", "さようなら",
    "ご自愛", "頑張って", "応援してる",
]


def is_farewell_message(message: str) -> bool:
    """メッセージが別れの挨拶かどうかを判定"""
    return any(keyword in message for keyword in FAREWELL_KEYWORDS)
