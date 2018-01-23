import asyncio
import logging

logger = logging.getLogger(__name__)
logger.info("loading...")

evtloop = asyncio.get_event_loop()