


## usage 

### prod


add 
`alias vibe="uv --project "YOUR_PROJECT_PATH_GOES_HERE" run call-my-agent`

of course `YOUR_PROJECT_PATH_GOES_HERE` need to match yours, edit it.

## CI

`uv.lock` is the source of truth for Python dependencies: CI runs
`uv sync --locked`, so it fails if the lockfile is stale.

`.github/workflows/actions.lock` pins the GitHub Actions used by the workflows.
After adding or changing an action reference, update it with:

```
gh actions-lock
```

CI verifies it with `gh actions-lock --verify`; offline coverage can be checked
with `gh actions-lock --verify-local`.

## Docker image

`.github/workflows/publish-image.yml` publishes a multi-arch (`amd64` and
`arm64`) image to `ghcr.io/kraktus/call-my-agent` every Monday at 05:17 UTC,
and on demand from the Actions tab. It publishes `latest`, `weekly` (on
scheduled runs), and `sha-<short>` tags.

If the GHCR package is private, log in first:

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

Then pull the image:

```bash
docker pull ghcr.io/kraktus/call-my-agent:latest
```

Run the agent from the project directory it should work on. Mount the project
at `/home/linuxbrew/<project-name>`, and persist OpenCode config and session
data from your host:

```bash
PROJECT="$(basename "$PWD")"
mkdir -p "$HOME/.config/opencode" "$HOME/.local/share/opencode"

docker run --rm -it \
  --env TERM \
  --mount "type=bind,src=$PWD,dst=/home/linuxbrew/$PROJECT" \
  --mount "type=bind,src=$HOME/.config/opencode,dst=/home/linuxbrew/.config/opencode" \
  --mount "type=bind,src=$HOME/.local/share/opencode,dst=/home/linuxbrew/.local/share/opencode" \
  --workdir "/home/linuxbrew/$PROJECT" \
  ghcr.io/kraktus/call-my-agent:latest
```

This starts the same tmux layout as the CLI: OpenCode in the top pane and a
shell in the bottom pane. Add more `--mount` options (for example your SSH keys
or `~/.config/gh`) if the agent needs them.

Arguments are run as a shell command inside the container, so a one-off command
can be used instead of starting tmux:

```bash
docker run --rm ghcr.io/kraktus/call-my-agent:latest "opencode --version"
```

The published image uses UID/GID `501:20` (macOS defaults). If those do not
match your host user, build a local image with your IDs:

```bash
uv run -m call_my_agent gen-dockerfile > Dockerfile
docker build \
  --build-arg UID="$(id -u)" \
  --build-arg GID="$(id -g)" \
  -t call-my-agent .
```

Then replace `ghcr.io/kraktus/call-my-agent:latest` with `call-my-agent` in the
commands above.

By default the CLI pulls and runs the published image. Pass `--local` to build
and use a local image with your UID/GID instead:

```bash
uv run call-my-agent --local
```

`--rebuild` refreshes the brew packages and `--no-cache` performs a full
rebuild; both imply `--local`.

## debug

`uv run -m call_my_agent --local --rebuild`

## debug

check your gid and uid with `id -u` and `id -g` and then run:

check all groups you're in
check all groups you're indepted in with `id -Gn`
check who can read and write in a dir with `ls -l` and check the group ownership of the dir with `ls -ld`
