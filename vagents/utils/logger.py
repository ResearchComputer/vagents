import os
import sys
from loguru import logger

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()

logger.remove()
logger.add(sys.stdout, level=LOGLEVEL)
