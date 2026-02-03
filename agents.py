"""AIエージェントクラス定義"""

import re

from openai import OpenAI
from config import API_BASE_URL, API_KEY


def remove_think_tags(text: str) -> str:
    """<think>...</think> タグとその内容を除去"""
    # 複数行にまたがる場合も対応
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


class Agent:
    """LMStudio APIを使用するAIエージェント"""

    def __init__(self, name: str, system_prompt: str, model: str):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.client = OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY,
        )
        self.conversation_history: list[dict] = []

    def add_message(self, role: str, content: str, name: str | None = None):
        """会話履歴にメッセージを追加"""
        message = {"role": role, "content": content}
        if name:
            message["name"] = name
        self.conversation_history.append(message)

    def send_message(self, partner_message: str, partner_name: str) -> str:
        """相手のメッセージに対する応答を生成"""
        # 相手のメッセージを履歴に追加
        self.add_message("user", partner_message, partner_name)

        # API呼び出し用のメッセージを構築
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history,
        ]

        # 空の応答が返ってきた場合はリトライ
        max_retries = 3
        for _ in range(max_retries):
            # LMStudio APIを呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=256,
            )

            # 応答を取得し、<think>タグを除去
            raw_message = response.choices[0].message.content or ""
            assistant_message = remove_think_tags(raw_message)

            # 空でなければ採用
            if assistant_message:
                break
        else:
            # リトライしても空なら fallback
            assistant_message = "うん、そうだね。"

        # 自分の応答を履歴に追加
        self.add_message("assistant", assistant_message)

        return assistant_message

    def get_initial_message(self, initial_text: str) -> str:
        """会話を開始する最初のメッセージを取得"""
        # 自分の最初のメッセージを履歴に追加
        self.add_message("assistant", initial_text)
        return initial_text
