#!/bin/bash

export PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:$PATH"

# ~/.config/opencode is bind-mounted from the host. On some setups (e.g. macOS
# with virtiofs and a root-owned/ACL-protected host dir) it is readable but not
# writable inside the container, which breaks opencode's runtime files
# (service.json). Fall back to a writable copy of the config so opencode can
# still read the host config while writing its own state.
config_dir="$HOME/.config/opencode"
if [ -d "$config_dir" ] && ! touch "$config_dir/.write-test" 2>/dev/null; then
  export XDG_CONFIG_HOME="$HOME/.local/opencode-config"
  mkdir -p "$XDG_CONFIG_HOME/opencode"
  cp -a "$config_dir/." "$XDG_CONFIG_HOME/opencode/" 2>/dev/null || true
else
  rm -f "$config_dir/.write-test" 2>/dev/null
fi

if [ $# -eq 0 ]; then
  exec /home/linuxbrew/.linuxbrew/bin/zsh -i
else
  exec /home/linuxbrew/.linuxbrew/bin/zsh -c "$*"
fi
