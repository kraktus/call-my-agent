#!/bin/bash

# Agent launch function
call_my_agent() {
    local session_name="agent_session"

    # Keep passthrough OFF. OpenCode's terminal-capability queries can otherwise
    # leak their replies (e.g. "2026;2$y", "1;2;4c") into a pane. OSC 52
    # clipboard does not need passthrough; set-clipboard handles it.
    tmux set-option -g allow-passthrough off

    # Enable tmux clipboard integration (OSC 52)
    tmux set-option -g set-clipboard on

    # Check if session already exists
    tmux has-session -t "$session_name" 2>/dev/null
    
    if [ $? != 0 ]; then
        # Create the panes before starting OpenCode. Its startup terminal queries
        # must not race with split-window, or their replies can land in the shell
        # pane instead of the OpenCode pane. Remember the first pane by ID: the
        # mounted ~/.tmux.conf may set base-index/pane-base-index, so a hardcoded
        # "session:0.0" target would not exist.
        local opencode_pane
        opencode_pane=$(tmux new-session -d -P -F '#{pane_id}' -s "$session_name")
        
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
        tmux select-pane -t "$opencode_pane"

        # Preserve each argument safely while passing the command through tmux's
        # shell-command interface. Start only after the pane layout is settled.
        printf -v opencode_command '%q ' opencode "$@"
        tmux respawn-pane -k -t "$opencode_pane" "${opencode_command% }"
    fi
    
    # Attach to the session
    tmux attach-session -t "$session_name"
}

call_my_agent "$@"
