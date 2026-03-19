FROM homebrew/brew:latest

ARG UID=501
ARG GID=20

USER root

RUN usermod -u $UID linuxbrew && usermod -aG 20 linuxbrew

USER linuxbrew

# Install dependencies from Brewfile
COPY Brewfile /home/linuxbrew/.Brewfile
RUN brew bundle install --file /home/linuxbrew/.Brewfile

# Needed because otherwise the intermediate directories are owned by root and the agent user can't write to them
RUN mkdir -p /home/linuxbrew/.local/share/opencode \
    && mkdir -p /home/linuxbrew/.config/opencode

COPY assets/agent-entrypoint.sh /home/linuxbrew/agent-entrypoint.sh
# home of the user
WORKDIR /home/agent/workdir

ENTRYPOINT ["/bin/bash"]
# Default command
# CMD ["opencode"]
