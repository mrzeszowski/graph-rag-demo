import logging
import os
import sys


class ColorFormatter(logging.Formatter):
	COLORS = {
		"DEBUG": "\x1b[38;5;245m",  # grey
		"INFO": "\x1b[36m",         # cyan
		"WARNING": "\x1b[33m",      # yellow
		"ERROR": "\x1b[31m",        # red
		"CRITICAL": "\x1b[1;31m",   # bold red
	}
	RESET = "\x1b[0m"

	def __init__(self, use_color: bool = True):
		super().__init__("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
		self.use_color = use_color
		
	def format(self, record: logging.LogRecord) -> str:
		msg = super().format(record)
		if not self.use_color:
			return msg

		color = self.COLORS.get(record.levelname, "")
		if not color:
			return msg

		# Color only the prefix (before the first ': ') so the actual message remains uncolored.
		prefix, sep, rest = msg.partition(": ")
		if sep:
			return f"{color}{prefix}{self.RESET}{sep}{rest}"
		# Fallback if expected separator not found: color the whole line.
		return f"{color}{msg}{self.RESET}"