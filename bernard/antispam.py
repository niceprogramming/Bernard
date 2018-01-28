from . import config
from . import common
from . import database

import json
import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

#for more info on how some of this code works, see https://xkcd.com/208/ and https://xkcd.com/323/