#!/bin/sh

newTmuxSessionScript() {
  local SESSION_NAME=$1
  tmux new-session -s "$SESSION_NAME" -d
  tmux split-window -d -t "$SESSION_NAME"
  tmux split-window -d -t "$SESSION_NAME"
  tmux split-window -d -t "$SESSION_NAME"
  tmux set-window-option -t "$SESSION_NAME" main-pane-height 66%
  tmux select-layout -t "$SESSION_NAME" main-horizontal
  tmux send-keys -t "$SESSION_NAME".1 "uv run pyright src -w" C-m
  tmux send-keys -t "$SESSION_NAME".2 "uv run ruff format ." C-m
  tmux send-keys -t "$SESSION_NAME".4 "" C-m
  tmux attach-session -t "$SESSION_NAME"
}

newTmuxSessionScript call-my-agent