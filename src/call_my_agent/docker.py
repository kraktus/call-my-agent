#!/usr/bin/python3
#
# coding: utf-8
# Licence: GNU AGPLv3

""""""

from pathlib import Path
import os
import socket
import subprocess
import random
import time
from dataclasses import dataclass
from itertools import chain
import string
from typing import List, Optional, Any

from . import REPO_DIR, log, HOME

# Constants
IMAGE_NAME = "kraktus/call-my-agent"
OPENCODE_CONFIG_DIR = ".config/opencode/"
OPENCODE_SHARE_DIR = ".local/share/opencode"

CONTAINER_HOME = Path("/home/linuxbrew")
BREW_CACHE_DIR = CONTAINER_HOME / ".cache" / "Homebrew"

SCRIPTS_REPO_URL = "https://github.com/kraktus/scripts.git"
SCRIPTS_CONTAINER_DIR = CONTAINER_HOME / "scripts"


###########
# Classes #
###########


@dataclass(frozen=True)
class Bind:
    source: Path
    target: Path
    readonly: bool = False

    def to_docker_arg(self) -> list[str]:
        # target is in the container so obviously cannot exist here
        return [
            "--mount",
            f"type=bind,src={str(self.source.resolve(strict=True))},dst={str(self.target)}{',readonly' if self.readonly else ''}",
        ]


@dataclass(frozen=True)
class MountPath:
    src: Path
    target: Path

    @classmethod
    def from_home_path(cls, path: str) -> "MountPath":
        return cls(src=Path(HOME / path), target=Path(CONTAINER_HOME / path))

    def to_bind_if_exists(self) -> Optional[Bind]:
        if self.src.exists():
            return Bind(source=self.src, target=self.target)
        else:
            return None

    def make_dir(self) -> str:
        return f"mkdir -p {str(self.target)}"


#############
# Functions #
#############


def get_mount_paths() -> list[MountPath]:
    return [
        MountPath.from_home_path(x)
        for x in [".config/opencode", ".local/share/opencode"]
    ]


def join_but_not_last(lst: list[str], sep: str) -> str:
    if len(lst) == 0:
        return ""
    elif len(lst) == 1:
        return lst[0]
    else:
        return sep.join(lst[:-1]) + sep + lst[-1]


def container_workdir(cwd: Path) -> Path:
    """Path of the mounted working directory inside the container."""
    return CONTAINER_HOME / cwd.name


def to_dockerfile(
    dirs_to_mount: list[MountPath], uid: int | None = None, gid: int | None = None
) -> str:
    if uid is None:
        uid = os.getuid()
    if gid is None:
        gid = os.getgid()
    brewfile_path = CONTAINER_HOME / ".Brewfile"
    return f"""# syntax=docker/dockerfile:1
FROM homebrew/brew:latest

    ARG UID=501
    ARG GID=20

    USER root

    RUN usermod -u $UID linuxbrew && usermod -aG $GID linuxbrew
    # Bump this arg to force only the brew layer (and later) to rebuild,
    # keeping the base image and user setup cached. --no-cache remains the full nuke.
    ARG BREW_REFRESH=0
    # Make the brew cache mount writable by the linuxbrew user. BuildKit cache
    # mounts persist across builds and are created root-owned, so own the cache
    # explicitly via the mount uid/gid and repair any pre-existing root-owned
    # cache. Referencing BREW_REFRESH makes this re-run on every --rebuild.
    RUN --mount=type=cache,target={BREW_CACHE_DIR},uid={uid},gid={gid} \\
        echo "brew cache refresh: $BREW_REFRESH" \\
        && chown -R linuxbrew:linuxbrew {BREW_CACHE_DIR}

    USER linuxbrew

    # Install dependencies from Brewfile, keeping the download cache across rebuilds
    COPY Brewfile {brewfile_path}
    RUN --mount=type=cache,target={BREW_CACHE_DIR},uid={uid},gid={gid} \\
        echo "brew refresh: $BREW_REFRESH" \\
        && brew update \\
        && brew bundle install --file {brewfile_path}

    # Needed because otherwise the intermediate directories are owned by root and the agent user can't write to them
    RUN {join_but_not_last([p.make_dir() for p in dirs_to_mount], " && ")}

    COPY assets/agent-entrypoint.sh {CONTAINER_HOME}/agent-entrypoint.sh
    COPY assets/opencode-tmux.sh {CONTAINER_HOME}/opencode-tmux.sh
    USER root
    RUN chmod +x {CONTAINER_HOME}/agent-entrypoint.sh {CONTAINER_HOME}/opencode-tmux.sh
    # Switch the default shell of the linuxbrew user to zsh
    RUN echo /home/linuxbrew/.linuxbrew/bin/zsh >> /etc/shells && usermod -s /home/linuxbrew/.linuxbrew/bin/zsh linuxbrew
    COPY assets/zshrc {CONTAINER_HOME}/.zshrc
    RUN chown linuxbrew:linuxbrew {CONTAINER_HOME}/.zshrc
    USER linuxbrew
    # Fetch the scripts repo (shallow clone, no history) to provide the zsh aliases
    RUN git clone --depth 1 {SCRIPTS_REPO_URL} {SCRIPTS_CONTAINER_DIR}

    ENTRYPOINT ["{CONTAINER_HOME}/agent-entrypoint.sh"]
    CMD ["{CONTAINER_HOME}/opencode-tmux.sh"]
    """


def run(
    cmd: List[str], check: bool = True, *args: Any, **kwargs: Any
) -> subprocess.CompletedProcess[Any]:
    """
    Executes a shell command, checks for success, and returns its stdout.

    Args:
        args: A list of strings representing the command and its arguments.

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code.
    """
    log.debug(f"Running command: {' '.join(cmd)}")
    res = subprocess.run(cmd, *args, check=check, text=True, **kwargs)
    return res


def random_string(length: int):
    return "".join(random.choices(string.ascii_lowercase, k=length))


def build_image(
    uid: int, gid: int, dockerfile: str, no_cache: bool = False, refresh: bool = False
):
    log.info(f"Building Docker image {IMAGE_NAME} with u:{uid} g:{gid}...")
    cmd = [
        "docker",
        "build",
        "--build-arg",
        f"UID={uid}",
        "--build-arg",
        f"GID={gid}",
    ]
    if no_cache:
        cmd.append("--no-cache")
    if refresh:
        # Only invalidates the brew layer and the layers after it
        cmd.extend(["--build-arg", f"BREW_REFRESH={int(time.time())}"])
    cmd.extend(
        [
            "-f",
            "-",
            str(REPO_DIR),
            "-t",
            IMAGE_NAME,
        ]
    )
    run(
        cmd,
        input=dockerfile,
        env={**os.environ, "DOCKER_BUILDKIT": "1"},
    )
    log.info(f"Builf of {IMAGE_NAME} successful")


def image_already_exists() -> bool:
    res = run(["docker", "images", "-q", IMAGE_NAME], check=False)
    return res != ""


def port_args(ports: list[int]) -> list[str]:
    """Map container ports to host, skipping any port already in use on the host."""
    args = []
    for port in ports:
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).bind(("0.0.0.0", port))
            args.extend(["-p", f"{port}:{port}"])
        except OSError:
            log.warning(f"Port {port} already in use on the host, not publishing")
    return args


# we're reinvinting the docker package...
def run_container(
    binds: list[Bind],
    workdir: Path,
    agent_args: list[str],
    ports: list[int] | None = None,
) -> None:
    container_name = f"call-my-agent-{random_string(5)}"
    binds_args = list(chain.from_iterable(bind.to_docker_arg() for bind in binds))
    publish_args = port_args(ports or [])
    env_args = ["--env", f"TERM={os.environ['TERM']}"] if "TERM" in os.environ else []
    print(binds_args)
    run(
        [
            "docker",
            "run",
            "--rm",  # Always remove after execution
            "--name",
            container_name,
            "-it",
            "--workdir",
            str(workdir),
            *binds_args,
            *publish_args,
            *env_args,
            IMAGE_NAME,
            *agent_args,
        ],
        check=False,
    )
    log.info(f"container {container_name} stopped.")


def run_agent(
    cwd: Path,
    uid: int,
    gid: int,
    agent_args: list[str] | None,
    rebuild: bool = False,
    no_cache: bool = False,
    ports: list[int] | None = None,
):
    mount_paths = get_mount_paths()
    if agent_args is None:
        agent_args = []
    if rebuild or no_cache or not image_already_exists():
        build_image(
            uid=uid,
            gid=gid,
            dockerfile=to_dockerfile(mount_paths, uid=uid, gid=gid),
            no_cache=no_cache,
            refresh=rebuild,
        )
    else:
        log.info(f"Using existing image {IMAGE_NAME}")

    # Config mounts
    binds = [Bind(source=cwd, target=container_workdir(cwd))]
    for path in mount_paths:
        if target := path.to_bind_if_exists():
            binds.append(target)

    tmux_conf_path = Path(HOME / ".tmux.conf")
    if tmux_conf_path.exists():
        binds.append(
            Bind(
                source=tmux_conf_path,
                target=CONTAINER_HOME / ".tmux.conf",
                readonly=True,
            )
        )

    run_container(
        binds=binds,
        workdir=container_workdir(cwd),
        agent_args=agent_args,
        ports=ports,
    )
