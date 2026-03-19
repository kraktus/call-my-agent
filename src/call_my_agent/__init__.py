#!/usr/bin/python3
#
# coding: utf-8
# Licence: GNU AGPLv3

""""""

import logging
import logging.handlers
import sys

from pathlib import Path

LOG_PATH = f"{__package__}.log"

REPO_DIR = Path(__file__).resolve(strict=True).parent.parent
HOME = Path.home().resolve(strict=True)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
format_string = "%(asctime)s | %(levelname)-8s | %(message)s"

# 125000000 bytes = 12.5Mb
handler = logging.handlers.RotatingFileHandler(
    LOG_PATH, maxBytes=12500000, backupCount=3, encoding="utf8"
)
handler.setFormatter(logging.Formatter(format_string))
handler.setLevel(logging.DEBUG)
log.addHandler(handler)

handler_2 = logging.StreamHandler(sys.stdout)
handler_2.setFormatter(logging.Formatter(format_string))
handler_2.setLevel(logging.INFO)
if __debug__:
    handler_2.setLevel(logging.DEBUG)
log.addHandler(handler_2)
