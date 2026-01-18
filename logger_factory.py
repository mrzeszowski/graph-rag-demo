import os
import sys
import logging

from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping

from color_formatter import ColorFormatter


class ContextLoggerAdapter(logging.LoggerAdapter):
	"""Logger adapter that appends context as key=value pairs.

	This keeps logs readable in the terminal and preserves context when using
	plain formatters or RichHandler.
	"""

	def process(self, msg: str, kwargs: MutableMapping[str, Any]):
		ctx = dict(self.extra or {})

		# `logging.Logger` only accepts a small set of keyword args.
		# Anything else (e.g. `path=...`, `run_id=...`) would raise:
		#   TypeError: Logger._log() got an unexpected keyword argument
		# So we capture arbitrary kwargs into context.
		extra = kwargs.pop("extra", None)
		if isinstance(extra, Mapping):
			ctx.update(extra)

		reserved = {"exc_info", "stack_info", "stacklevel"}
		for k in list(kwargs.keys()):
			if k in reserved:
				continue
			ctx[k] = kwargs.pop(k)

		# Prevent stdlib logging from trying to interpret our context as record attrs.
		kwargs["extra"] = {}

		ctx = _filter_context(ctx)
		if ctx:
			suffix = " ".join(f"{k}={_format_ctx_value(k, ctx[k])}" for k in sorted(ctx.keys()))
			msg = f"{msg} | {suffix}"
		return msg, kwargs


_DEFAULT_CONTEXT_KEYS_MINIMAL = (
	"run_id",
	#"source",
	"op",
	"question",
	"path",
	"latency_s",
	#"vector_index",
	#"vector_store_id",
	#"count",
	#"chunks",
	#"files",
	#"bytes",
	"name",
	"run_dir",
)


def _context_mode() -> str:
	# Options:
	# - none: don't append any context
	# - minimal: append a small allow-list (default)
	# - all: append everything captured by the adapter
	return os.getenv("LOG_CONTEXT", "minimal").strip().lower()


def _parse_keys_env(var_name: str) -> set[str]:
	raw = os.getenv(var_name, "")
	if not raw.strip():
		return set()
	# Support commas and/or whitespace.
	parts = [p.strip() for p in raw.replace(",", " ").split()]
	return {p for p in parts if p}


def _filter_context(ctx: Mapping[str, Any]) -> dict[str, Any]:
	mode = _context_mode()
	if mode in {"0", "off", "false", "none"}:
		return {}

	filtered = dict(ctx)

	if mode not in {"all", "full"}:
		allow = _parse_keys_env("LOG_CONTEXT_KEYS") or set(_DEFAULT_CONTEXT_KEYS_MINIMAL)
		filtered = {k: v for k, v in filtered.items() if k in allow}

	exclude = _parse_keys_env("LOG_CONTEXT_EXCLUDE_KEYS")
	for k in exclude:
		filtered.pop(k, None)

	return filtered


def _format_ctx_value(key: str, value: Any) -> str:
	# Keep log lines compact and readable.
	max_len_str = os.getenv("LOG_CONTEXT_VALUE_MAXLEN", "120").strip()
	try:
		max_len = int(max_len_str)
	except ValueError:
		max_len = 120

	text = str(value)
	# For paths, show only the basename by default.
	if key in {"path", "run_dir"} and ("/" in text or "\\" in text):
		text = os.path.basename(text)

	if max_len > 0 and len(text) > max_len:
		text = text[: max_len - 1] + "…"

	# Quote values with spaces to keep key=value parsing readable.
	if any(ch.isspace() for ch in text):
		return f'"{text}"'
	return text


def bind(logger: logging.Logger, **context: Any) -> ContextLoggerAdapter:
	return ContextLoggerAdapter(logger, context)


def new_run_id() -> str:
	# ISO timestamp is good enough for local runs; override via env if needed.
	return os.getenv("RUN_ID") or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _maybe_add_file_handler(logger: logging.Logger) -> None:
	log_file = os.getenv("LOG_FILE")
	if not log_file:
		return
	if any(getattr(h, "baseFilename", None) == log_file for h in logger.handlers):
		return
	file_handler = logging.FileHandler(log_file, encoding="utf-8")
	file_handler.setLevel(logger.level)
	file_handler.setFormatter(
		logging.Formatter(
			"[%(asctime)s] %(levelname)s %(name)s: %(message)s",
			"%Y-%m-%dT%H:%M:%S%z",
		)
	)
	logger.addHandler(file_handler)


def _build_console_handler(*, use_color: bool) -> logging.Handler:
	fmt = os.getenv("LOG_FORMAT", "rich").lower()
	if fmt == "plain":
		h = logging.StreamHandler(stream=sys.stdout)
		h.setFormatter(ColorFormatter(use_color=use_color))
		return h

	# Default: rich
	try:
		from rich.logging import RichHandler

		h = RichHandler(
			rich_tracebacks=True,
			show_time=True,
			show_level=True,
			show_path=False,
		)
		h.setFormatter(logging.Formatter("%(message)s"))
		return h
	except Exception:
		# Fall back to the existing color formatter.
		h = logging.StreamHandler(stream=sys.stdout)
		h.setFormatter(ColorFormatter(use_color=use_color))
		return h

def get_logger(name: str) -> logging.Logger:
	level_str = os.getenv("LOG_LEVEL", "INFO").upper()
	level = getattr(logging, level_str, logging.INFO)
	use_color = os.getenv("LOG_COLOR", "true").lower() in ("1", "true", "yes", "on")
	logger = logging.getLogger(name)
	logger.setLevel(level)
	if not logger.hasHandlers():
		handler = _build_console_handler(use_color=use_color)
		logger.addHandler(handler)
		_maybe_add_file_handler(logger)

	logging.getLogger("neo4j").setLevel(logging.INFO)
	# neo4j_graphrag can be very chatty at DEBUG; keep it at INFO by default.
	logging.getLogger("neo4j_graphrag").setLevel(logging.INFO)

	return logger
