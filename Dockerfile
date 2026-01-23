FROM homebrew/brew:latest

# Install dependencies from Brewfile
COPY Brewfile /home/.Brewfile
RUN brew bundle install --file /home/.Brewfile

# home of the user
WORKDIR /workdir

ENTRYPOINT ["./assets/agent-entrypoint.sh"]
# Default command
CMD ["opencode"]
