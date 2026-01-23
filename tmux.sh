#!/bin/sh

newTmuxSessionScript() {
  local SESSION_NAME=$1
  tmux new-session -s "$SESSION_NAME" -d
  tmux split-window -d
  tmux split-window -d
  tmux split-window -d
  tmux send-keys -t "$SESSION_NAME".1 "uv run pyright src -w" C-m
  tmux send-keys -t "$SESSION_NAME".2 "" C-m
  tmux send-keys -t "$SESSION_NAME".4 "" C-m
  tmux attach-session -t "$SESSION_NAME"
}

newTmuxSessionScript call-my-agent