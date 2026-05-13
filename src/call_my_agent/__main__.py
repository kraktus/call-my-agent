#!/usr/bin/python3
#
# coding: utf-8
# Licence: GNU AGPLv3

""""""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

from argparse import RawTextHelpFormatter
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List, Union, Tuple

from .docker import run_agent, to_dockerfile, get_mount_paths
from . import LOG_PATH, log

###########
# Classes #
###########


def doc(dic: Dict[str, Callable[..., Any]]) -> str:
    """Produce documentation for every command based on doc of each function"""
    doc_string = ""
    for name_cmd, func in dic.items():
        doc_string += f"{name_cmd}: {func.__doc__}\n\n"
    return doc_string


def run_cmd(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    run_agent(
        cwd=cwd,
        rebuild=args.rebuild,
        uid=args.uid,
        gid=args.gid,
        agent_args=args.agent_args,
    )

def gen_cmd(args: argparse.Namespace) -> None:
    print(to_dockerfile(get_mount_paths()))

def main() -> None:
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--rebuild", action="store_true", help="Force rebuilding the Docker image"
    )
    parent_parser.add_argument(
        "--uid",
        "-u",
        type=int,
        default=os.getuid(),
        help="User ID to use inside the Docker container",
    )
    parent_parser.add_argument(
        "--gid",
        "-g",
        type=int,
        default=os.getgid(),
        help="Group ID to use inside the Docker container",
    )
    parent_parser.add_argument(
        "--agent-args",
        nargs="*",
        help="Arguments to pass to the agent (prefix each time by append)",
    )

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, parents=[parent_parser])
    parser.set_defaults(func=run_cmd)

    subparsers = parser.add_subparsers(
        dest="command",
        help="Command to execute (default: run)"
    )

    run_parser = subparsers.add_parser(
        "run", 
        parents=[parent_parser], 
        help="Run the agent (default)"
    )
    run_parser.set_defaults(func=run_cmd)

    gen_parser = subparsers.add_parser(
        "gen-dockerfile", 
        help="Output the Dockerfile to stdout. Recommended usage:\n%(prog)s > Dockerfile"
    )
    gen_parser.set_defaults(func=gen_cmd)

    args = parser.parse_args()

    try:
        args.func(args)
    except Exception as e:
        log.error(f"Error running agent: {e}")
        traceback.print_exc()
        sys.exit(1)


########
# Main #
########

if __name__ == "__main__":
    if "gen-dockerfile" not in sys.argv:
        print("#" * 80)
    main()
