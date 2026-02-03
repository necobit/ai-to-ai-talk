#!/usr/bin/env python3
"""AI会話システム セットアップスクリプト（モデル選択のみ）"""

import json
import sys

from openai import OpenAI

API_BASE_URL = "http://127.0.0.1:1234/v1"
CONFIG_FILE = "/tmp/ai_conversation_config.json"


def get_available_models() -> list[str]:
    """LMStudioから利用可能なモデル一覧を取得"""
    try:
        client = OpenAI(base_url=API_BASE_URL, api_key="lm-studio")
        models = client.models.list()
        return [model.id for model in models.data]
    except Exception as e:
        print(f"エラー: LMStudioに接続できません。サーバーが起動しているか確認してください。")
        print(f"詳細: {e}")
        sys.exit(1)


def select_model(models: list[str]) -> str:
    """モデルを選択"""
    print("【モデル選択】使用するLLMモデルを選んでください：")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")

    while True:
        try:
            choice = input(f"番号を入力 (1-{len(models)}): ").strip()
            if not choice:
                return models[0]
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
            print(f"1から{len(models)}の間で入力してください")
        except ValueError:
            print("数字を入力してください")


def main():
    print("=== AI会話システム設定 ===\n")

    # モデル一覧を取得
    models = get_available_models()
    if not models:
        print("エラー: 利用可能なモデルがありません")
        sys.exit(1)

    # モデル選択
    model = select_model(models)
    print(f"選択: {model}\n")

    # 設定をJSONファイルに保存
    config = {
        "model": model,
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("ロールと話題はLLMがランダムに生成します。")
    print("会話を開始します...\n")


if __name__ == "__main__":
    main()
