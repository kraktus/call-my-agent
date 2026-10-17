


## usage 

### prod


add 
`alias vibe="uv --project "YOUR_PROJECT_PATH_GOES_HERE" run call-my-agent`

of course `YOUR_PROJECT_PATH_GOES_HERE` need to match yours, edit it.

## CI and container image

`uv.lock` is the source of truth for Python dependencies: CI runs
`uv sync --locked`, so it fails if the lockfile is stale.

`.github/workflows/actions.lock` pins the GitHub Actions used by the workflows.
After adding or changing an action reference, update it with:

```
gh actions-lock
```

CI verifies it with `gh actions-lock --verify`; offline coverage can be checked
with `gh actions-lock --verify-local`.

`.github/workflows/publish-image.yml` publishes a multi-arch image to
`ghcr.io/kraktus/call-my-agent` every Monday at 05:17 UTC, and can also be run
manually from the Actions tab. It publishes `latest`, `weekly` (on scheduled
runs), and `sha-<short>` tags.

## debug

`uv run -m call_my_agent --rebuild`

## debug

check your gid and uid with `id -u` and `id -g` and then run:

check all groups you're in
check all groups you're indepted in with `id -Gn`
check who can read and write in a dir with `ls -l` and check the group ownership of the dir with `ls -ld`
