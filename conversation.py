#!/usr/bin/env python3
"""AI同士の会話システム メインスクリプト"""

import argparse
import json
import re
import signal
import time

from openai import OpenAI
from rich.console import Console

from agents import Agent
from config import (
    API_BASE_URL,
    API_KEY,
    MAX_TURNS,
    CHAR_FILE,
    create_system_prompt,
    is_farewell_message,
    load_user_config,
    load_characters,
)

# グローバル変数（シグナルハンドラ用）
running = True


def signal_handler(signum, frame):
    """Ctrl+Cハンドラ"""
    global running
    running = False
    print("\n\n会話を終了します...")


def print_typing(console: Console, name: str, message: str, delay: float = 0.05):
    """1文字ずつタイピング風に表示"""
    console.print(f"[bold cyan]{name}:[/bold cyan] ", end="")
    for char in message:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()  # 改行
    print()  # 空行


def generate_random_session(client: OpenAI, model: str, previous_roles: list[str]) -> dict | None:
    """LLMを使ってランダムなロール・話題・キャラクターを生成"""

    import random

    # ランダムシードを生成して多様性を促す
    seed_words = ["朝", "昼", "夜", "春", "夏", "秋", "冬", "雨", "晴れ", "月曜", "金曜", "休日"]
    seed = random.choice(seed_words)
    random_num = random.randint(1, 100)

    # 避けるべき設定
    avoid_text = ""
    if previous_roles:
        avoid_list = ", ".join(previous_roles[-5:])  # 直近5つを避ける
        avoid_text = f"\n\n【禁止】以下の設定は既に使用済みなので絶対に使わないでください: {avoid_list}"

    json_template = '''
{
  "role": "関係性（例：友人同士、先輩と後輩、店員と客など）",
  "topic": "話題（例：週末の予定、最近ハマっていること、仕事の悩みなど）",
  "A": {
    "name": "名前（日本人の名前、カタカナ）",
    "role_description": "役割の説明（例：大学生、カフェ店員、会社の先輩など）",
    "age": 年齢（数字）,
    "gender": "male または female",
    "pronoun": "一人称（俺/僕/私など）",
    "formality": "話し方（casual=タメ口 / polite=丁寧語 / respectful=敬語）",
    "speech_example": "話し方の例（3つ程度）"
  },
  "B": {
    "name": "名前（Aと被らない）",
    "role_description": "役割の説明",
    "age": 年齢（数字）,
    "gender": "male または female",
    "pronoun": "一人称",
    "formality": "話し方",
    "speech_example": "話し方の例"
  },
  "relation": "二人の関係性の詳細説明",
  "initial_message": "Aが最初に発する自然な会話の開始メッセージ"
}
'''

    prompt = f"""ランダムで面白い2人の会話設定を生成してください。
（シード: {seed}、番号: {random_num}）{avoid_text}

以下のJSON形式のみを出力してください。他の文章は一切出力しないでください。
{json_template}
バリエーション豊かに、以下のような様々な関係性から選んでください：
- 友人、幼なじみ、同僚、先輩と後輩、上司と部下
- 店員と客、医者と患者、教師と生徒
- 親子、兄弟姉妹、恋人、夫婦
- 趣味仲間、ネット友達、バイト仲間
- 美容師と客、タクシー運転手と乗客、配達員と受取人

話題も多様に：日常、趣味、仕事、恋愛、悩み相談、おすすめ紹介、思い出話など"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは会話設定を生成するアシスタントです。JSONのみを出力してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,  # ランダム性を高める
            max_tokens=1024,
        )

        result = response.choices[0].message.content

        # <think>タグを除去
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()

        # JSON部分を抽出
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            result = json_match.group()

        return json.loads(result)

    except Exception as e:
        print(f"セッション生成エラー: {e}")
        return None


def run_session(agent_id: str, console: Console, model: str, session_num: int, previous_roles: list[str]) -> tuple[bool, str | None]:
    """1セッションの会話を実行。成功フラグと使用したロールを返す"""
    global running

    # 共有ファイルのパス
    message_file = "/tmp/ai_conversation_message.txt"
    turn_file = "/tmp/ai_conversation_turn.txt"

    if agent_id == "A":
        # Agent Aがセッション設定を生成
        console.print(f"[bold magenta]━━━ セッション {session_num} ━━━[/bold magenta]")
        console.print("[dim]設定を生成中...[/dim]\n")

        client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
        chars = generate_random_session(client, model, previous_roles)

        if chars is None:
            console.print("[red]設定生成に失敗しました。リトライします...[/red]")
            return False, None

        used_role = chars.get("role", "不明")

        # キャラクター情報を保存
        with open(CHAR_FILE, "w") as f:
            json.dump(chars, f, ensure_ascii=False, indent=2)

        # 設定を表示
        console.print(f"[dim]ロール: {chars.get('role', '不明')}[/dim]")
        console.print(f"[dim]話題: {chars.get('topic', '不明')}[/dim]\n")

        my_char = chars["A"]
        partner_char = chars["B"]
    else:
        # Agent Bはキャラクター情報を待つ
        console.print(f"[bold magenta]━━━ セッション {session_num} ━━━[/bold magenta]\n")

        while running:
            chars = load_characters()
            if chars is not None:
                break
            time.sleep(0.3)

        if not running:
            return False, None

        used_role = chars.get("role", "不明")
        my_char = chars["B"]
        partner_char = chars["A"]

    my_name = my_char["name"]
    partner_name = partner_char["name"]
    relation = chars.get("relation", "会話相手")
    topic = chars.get("topic", "雑談")

    # システムプロンプトを生成
    system_prompt = create_system_prompt(my_char, partner_name, relation, topic)
    my_agent = Agent(my_name, system_prompt, model)

    # 役割を表示
    console.print(f"[bold green]{my_name}[/bold green]（{my_char['role_description']}）\n")

    turn = 0
    last_message = ""
    farewell_count = 0

    if agent_id == "A":
        time.sleep(0.5)

        # 初期メッセージを取得
        initial = chars.get("initial_message", f"ねえ{partner_name}、{topic}について話そうよ！")
        my_agent.get_initial_message(initial)
        print_typing(console, my_name, initial)

        with open(message_file, "w") as f:
            f.write(initial)
        with open(turn_file, "w") as f:
            f.write("B")

        turn = 1
        last_message = initial

        while running and turn < MAX_TURNS:
            time.sleep(0.3)

            try:
                with open(turn_file, "r") as f:
                    current_turn = f.read().strip()
            except FileNotFoundError:
                continue

            if current_turn == "A":
                with open(message_file, "r") as f:
                    partner_message = f.read().strip()

                if partner_message and partner_message != last_message:
                    partner_said_farewell = is_farewell_message(partner_message)
                    if partner_said_farewell:
                        farewell_count += 1

                    response = my_agent.send_message(partner_message, partner_name)
                    print_typing(console, my_name, response)

                    my_farewell = is_farewell_message(response)
                    if my_farewell:
                        farewell_count += 1

                    with open(message_file, "w") as f:
                        f.write(response)

                    if farewell_count >= 2:
                        with open(turn_file, "w") as f:
                            f.write("END")
                        break

                    with open(turn_file, "w") as f:
                        f.write("B")

                    last_message = response
                    turn += 1

                    if not partner_said_farewell and not my_farewell:
                        farewell_count = 0

            elif current_turn == "END":
                break

    else:
        while running and turn < MAX_TURNS:
            time.sleep(0.3)

            try:
                with open(turn_file, "r") as f:
                    current_turn = f.read().strip()
            except FileNotFoundError:
                continue

            if current_turn == "END":
                break

            if current_turn == "B":
                try:
                    with open(message_file, "r") as f:
                        partner_message = f.read().strip()
                except FileNotFoundError:
                    continue

                if partner_message and partner_message != last_message:
                    partner_said_farewell = is_farewell_message(partner_message)
                    if partner_said_farewell:
                        farewell_count += 1

                    response = my_agent.send_message(partner_message, partner_name)
                    print_typing(console, my_name, response)

                    my_farewell = is_farewell_message(response)
                    if my_farewell:
                        farewell_count += 1

                    with open(message_file, "w") as f:
                        f.write(response)

                    if farewell_count >= 2:
                        with open(turn_file, "w") as f:
                            f.write("END")
                        break

                    with open(turn_file, "w") as f:
                        f.write("A")

                    last_message = response
                    turn += 1

                    if not partner_said_farewell and not my_farewell:
                        farewell_count = 0

    console.print(f"[dim]（{turn}ターンで終了）[/dim]\n")
    return True, used_role


def run_conversation(agent_id: str):
    """会話ループを実行"""
    global running

    console = Console()
    user_config = load_user_config()
    model = user_config["model"]

    session_num = 1
    previous_roles: list[str] = []  # 過去に使用したロールを記録

    while running:
        # 一時ファイルをクリア（Agent Aのみ）
        if agent_id == "A":
            import os
            for f in ["/tmp/ai_conversation_message.txt", "/tmp/ai_conversation_turn.txt", "/tmp/ai_conversation_chars.json"]:
                try:
                    os.remove(f)
                except FileNotFoundError:
                    pass
            time.sleep(0.3)

        # セッション実行
        success, used_role = run_session(agent_id, console, model, session_num, previous_roles)

        if not running:
            break

        if success:
            # 使用したロールを記録（重複防止用）
            if used_role:
                previous_roles.append(used_role)
            session_num += 1
            # 次のセッションまで少し待つ
            console.print("[dim]次のセッションを準備中...[/dim]\n")
            time.sleep(2)
        else:
            time.sleep(1)

    console.print("[yellow]プログラムを終了しました[/yellow]")


def main():
    parser = argparse.ArgumentParser(description="AI同士の会話システム")
    parser.add_argument(
        "--agent",
        "-a",
        choices=["A", "B"],
        required=True,
        help="担当するAIエージェント",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    run_conversation(args.agent)


if __name__ == "__main__":
    main()
