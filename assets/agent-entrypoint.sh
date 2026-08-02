#!/bin/bash

export PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:$PATH"

if [ $# -eq 0 ]; then
  exec /home/linuxbrew/.linuxbrew/bin/zsh -i
else
  exec /home/linuxbrew/.linuxbrew/bin/zsh -c "$*"
fi
