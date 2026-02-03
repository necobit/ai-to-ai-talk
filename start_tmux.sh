#!/bin/bash
# AI同士の会話システム - tmux起動スクリプト

SESSION_NAME="ai-talk"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# tmuxセッション内から実行している場合は$TMUXをunset
if [ -n "$TMUX" ]; then
    unset TMUX
fi

# 既存のconversation.pyプロセスを終了
pkill -f "python.*conversation.py" 2>/dev/null

# 既存のセッションがあれば先に終了
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    # セッションが完全に終了するまで待機
    while tmux has-session -t "$SESSION_NAME" 2>/dev/null; do
        sleep 0.5
    done
fi

# プロセス終了を確実に待つ
sleep 2

# 入力バッファをクリア
stty sane 2>/dev/null
while read -t 0.1 -n 1000 discard 2>/dev/null; do :; done

# 一時ファイルをクリア
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

# 新しいtmuxセッションを作成（プロセス終了後もペインを維持）
tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR"
tmux set-option -t "$SESSION_NAME" remain-on-exit on

# ペインを垂直分割
tmux split-window -h -t "$SESSION_NAME" -c "$SCRIPT_DIR"

# セッションが安定するまで待機
sleep 1

# 左ペイン（AI-A）でスクリプトを実行
tmux send-keys -t "$SESSION_NAME:0.0" "cd $SCRIPT_DIR && source $VENV_DIR/bin/activate && python conversation.py --agent A" C-m

# Agent Aが先に起動するように待機
sleep 1

# 右ペイン（AI-B）でスクリプトを実行
tmux send-keys -t "$SESSION_NAME:0.1" "cd $SCRIPT_DIR && source $VENV_DIR/bin/activate && python conversation.py --agent B" C-m

# セッションにアタッチ
tmux attach-session -t "$SESSION_NAME"
