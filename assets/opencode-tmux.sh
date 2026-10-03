#!/bin/bash

# Agent launch function
call_my_agent() {
    local session_name="agent_session"

    # Keep passthrough OFF. Opencode wraps its terminal-capability queries in the
    # tmux passthrough DCS; when passthrough is on, the terminal's replies
    # (e.g. "2026;2$y", "1;2;4c") come back and leak as garbage into a pane.
    # OSC 52 clipboard does NOT need passthrough, set-clipboard handles it.
    tmux set-option -g allow-passthrough off

    # Enable tmux clipboard integration (OSC 52)
    tmux set-option -g set-clipboard on

    # Check if session already exists
    tmux has-session -t "$session_name" 2>/dev/null
    
    if [ $? != 0 ]; then
        # Create new detached session, running opencode in the first pane
        # Pass any arguments down to opencode
        tmux new-session -d -s "$session_name" "opencode $*"
        
        # Split the window vertically (creating rows) for standard shell prompts
        tmux split-window -v -t "$session_name"

        # Give the top (opencode) pane 66% of the height
        tmux set-window-option -t "$session_name" main-pane-height 66%
        tmux select-layout -t "$session_name" main-horizontal

        # Different prefix to avoid conflict with a host tmux
        tmux set-option -t "$session_name" prefix C-a
        
        # Change the tmux status bar color to blue as requested
        tmux set-option -t "$session_name" status-bg blue
        tmux set-option -t "$session_name" status-fg white
        
        # Return focus to the first pane (opencode)
        tmux select-pane -t "$session_name":0.0
    fi
    
    # Attach to the session
    tmux attach-session -t "$session_name"
}

call_my_agent "$@"
