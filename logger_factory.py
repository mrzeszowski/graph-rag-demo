import os
import sys
import logging

from color_formatter import ColorFormatter

def get_logger(name: str) -> logging.Logger:
	level_str = os.getenv("LOG_LEVEL", "INFO").upper()
	level = getattr(logging, level_str, logging.INFO)
	use_color = os.getenv("LOG_COLOR", "true").lower() in ("1", "true", "yes", "on")
	logger = logging.getLogger(name)
	logger.setLevel(level)
	if not logger.hasHandlers():
		handler = logging.StreamHandler(stream=sys.stdout)
		handler.setFormatter(ColorFormatter(use_color=use_color))
		logger.addHandler(handler)

	logging.getLogger("neo4j").setLevel(logging.INFO)
	logging.getLogger("neo4j_graphrag").setLevel(logging.INFO)

	return logger
