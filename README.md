


## usage 

### prod


add 
`alias vibe="uv --project "YOUR_PROJECT_PATH_GOES_HERE" run call-my-agent`

of course `YOUR_PROJECT_PATH_GOES_HERE` need to match yours, edit it.

## debug

`uv run -m call_my_agent --rebuild`

## debug

check your gid and uid with `id -u` and `id -g` and then run:

check all groups you're in
check all groups you're indepted in with `id -Gn`
check who can read and write in a dir with `ls -l` and check the group ownership of the dir with `ls -ld`
