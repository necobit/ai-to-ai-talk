#!/bin/bash
# AI同士の会話システム - tmux起動スクリプト

SESSION_NAME="ai-talk"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# tmuxセッション内から実行している場合は$TMUXをunset
if [ -n "$TMUX" ]; then
    unset TMUX
fi

# 既存のセッションがあれば先に終了（プロセスが残らないように）
tmux kill-session -t "$SESSION_NAME" 2>/dev/null
sleep 1

# 入力バッファをクリア
stty sane 2>/dev/null
while read -t 1 -n 1000 discard 2>/dev/null; do :; done

# 一時ファイルをクリア（セッション終了後に行う）
rm -f /tmp/ai_conversation_message.txt /tmp/ai_conversation_turn.txt /tmp/ai_conversation_chars.json /tmp/ai_conversation_config.json

# 仮想環境が存在しない場合は作成
if [ ! -d "$VENV_DIR" ]; then
    echo "仮想環境を作成中..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    echo "依存パッケージをインストール中..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
    deactivate
    echo "セットアップ完了"
    echo ""
fi

# セットアップスクリプトを実行（モデル選択）
source "$VENV_DIR/bin/activate"
python "$SCRIPT_DIR/setup.py"
SETUP_RESULT=$?
deactivate

# セットアップがキャンセルされた場合は終了
if [ $SETUP_RESULT -ne 0 ]; then
    echo "セットアップがキャンセルされました"
    exit 1
fi

# 新しいtmuxセッションを作成
tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR"

# ペインを垂直分割
tmux split-window -h -t "$SESSION_NAME" -c "$SCRIPT_DIR"

# 左ペイン（AI-A）でスクリプトを実行（仮想環境をアクティベート）
tmux send-keys -t "$SESSION_NAME:0.0" "source $VENV_DIR/bin/activate && python conversation.py --agent A" C-m

# 右ペイン（AI-B）でスクリプトを実行（仮想環境をアクティベート）
tmux send-keys -t "$SESSION_NAME:0.1" "source $VENV_DIR/bin/activate && python conversation.py --agent B" C-m

# セッションにアタッチ
tmux attach-session -t "$SESSION_NAME"
