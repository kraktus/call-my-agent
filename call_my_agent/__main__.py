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

from .docker import run_agent
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


def main() -> None:
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)

    parser.add_argument(
        "--rebuild", action="store_true", help="Force rebuilding the Docker image"
    )
    parser.add_argument("--agent-args", action="append", help="Arguments to pass to the agent (prefix each time by append)")

    args = parser.parse_args()

    # Current working directory
    cwd = Path.cwd()

    try:
        run_agent(
            cwd=cwd,
            rebuild=args.rebuild,
            agent_args=args.agent_args,
        )
    except Exception as e:
        log.error(f"Error running agent: {e}")
        traceback.print_exc()
        sys.exit(1)


########
# Main #
########

if __name__ == "__main__":
    print("#" * 80)
    main()
