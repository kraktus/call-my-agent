#!/bin/bash

# Agent launch function
call_my_agent() {
    local session_name="agent_session"
    
    # Check if session already exists
    tmux has-session -t "$session_name" 2>/dev/null
    
    if [ $? != 0 ]; then
        # Create new detached session, running opencode in the first pane
        # Pass any arguments down to opencode
        tmux new-session -d -s "$session_name" "opencode $*"
        
        # Split the window vertically (creating rows) for standard shell prompts
        tmux split-window -v -t "$session_name"
        tmux split-window -v -t "$session_name"
        
        # Make the 3 rows perfectly even
        tmux select-layout -t "$session_name" even-vertical

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
