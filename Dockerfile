FROM homebrew/brew:latest

# Install dependencies from Brewfile
COPY Brewfile /home/.Brewfile
RUN brew bundle install --file /home/.Brewfile

# Set up working directory
WORKDIR /workdir

# Default command
CMD ["opencode"]
