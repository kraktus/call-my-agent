FROM homebrew/brew:latest

ARG UID=501
ARG GID=20

USER root

# RUN adduser --uid $UID --gid $GID --disabled-password --gecos "" agent

USER agent

# Install dependencies from Brewfile
COPY Brewfile /home/agent/.Brewfile
RUN brew bundle install --file /home/agent/.Brewfile

COPY assets/agent-entrypoint.sh /home/agent/agent-entrypoint.sh
# home of the user
WORKDIR /home/agent/workdir

ENTRYPOINT ["/bin/bash"]
# Default command
# CMD ["opencode"]
