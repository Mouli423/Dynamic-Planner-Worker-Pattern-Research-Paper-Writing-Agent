# utils/logger.py
"""
Structured logging for the Research Paper Agent.
Imports NOTHING from research_agent.* — zero circular-import risk.

Usage
-----
from research_agent.utils.logger import log, setup_logging
setup_logging()

log.planner("Routing to introduction_writer", next_worker="introduction_writer")
log.worker("topic_clarifier", "Starting", status="running")
log.evaluation("background_writer", score=0.82, decision="accept")
log.circuit_breaker("Tripped", worker_name="outline_designer", consecutive=3)
log.error("LLM call failed", exc=e)
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

# ── ANSI colours ──────────────────────────────────────────────────────────────
_R = "\033[0m";  _B = "\033[1m";  _D = "\033[2m"
_C = {
    "DEBUG":   "\033[36m", "INFO":    "\033[37m", "SUCCESS": "\033[32m",
    "WARNING": "\033[33m", "ERROR":   "\033[31m", "CRITICAL":"\033[35m",
    "PLANNER": "\033[34m", "WORKER":  "\033[96m", "EVAL":    "\033[93m",
    "CIRCUIT": "\033[91m", "SUMMARY": "\033[92m",
}

# ── Custom log levels ─────────────────────────────────────────────────────────
SUCCESS  = 25;  PLANNER  = 22;  WORKER   = 21
EVAL     = 23;  CIRCUIT  = 45;  SUMMARY_ = 24

for _lvl, _name in [(SUCCESS,"SUCCESS"),(PLANNER,"PLANNER"),(WORKER,"WORKER"),
                    (EVAL,"EVAL"),(CIRCUIT,"CIRCUIT"),(SUMMARY_,"SUMMARY")]:
    logging.addLevelName(_lvl, _name)


class _ColourFmt(logging.Formatter):
    def format(self, record):
        colour = _C.get(record.levelname, "")
        ts     = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level  = f"{colour}{_B}{record.levelname:<8}{_R}"
        line   = f"{_D}{ts}{_R}  {level}  {_D}{record.name}{_R}  {record.getMessage()}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class _PlainFmt(logging.Formatter):
    def format(self, record):
        ts   = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts}  [{record.levelname:<8}]  {record.name}  {record.getMessage()}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class AgentLogger:
    def __init__(self, name="research_agent"):
        self._l = logging.getLogger(name)

    def debug(self, msg, **kw):    self._l.debug(msg, **kw)
    def info(self, msg, **kw):     self._l.info(msg, **kw)
    def warning(self, msg, **kw):  self._l.warning(msg, **kw)
    def critical(self, msg, **kw): self._l.critical(msg, **kw)

    def error(self, msg: str, exc: Exception = None, **kw):
        if exc:
            self._l.log(logging.ERROR, f"{msg}: {exc}", exc_info=exc, **kw)
        else:
            self._l.error(msg, **kw)

    def success(self, msg):
        self._l.log(SUCCESS, f"✓  {msg}")

    def planner(self, msg, next_worker=None, step=None):
        parts = [f"🗺  {msg}"]
        if next_worker: parts.append(f"→ {next_worker}")
        if step is not None: parts.append(f"(step {step})")
        self._l.log(PLANNER, "  ".join(parts))

    def worker(self, name, msg, worker_output="working...",status="running"):
        icons = {"running":"⚙","success":"✅","failure":"❌","skipped":"⏭","retry":"🔁"}
        self._l.log(WORKER, f"{icons.get(status,'•')}  [{name}]  {msg} [{worker_output}]")

    def evaluation(self, name, score, decision, issues=None):
        bar = "█"*int(score*10) + "░"*(10-int(score*10))
        msg = f"[{name}]  score={score:.2f}  [{bar}]  → {'PASS' if decision=='accept' else 'RETRY'}"
        if issues: msg += f"  issues={issues[:2]}"
        self._l.log(EVAL, msg)

    def circuit_breaker(self, event, worker_name=None, consecutive=None):
        parts = [f"🔴  CIRCUIT BREAKER  {event}"]
        if worker_name:      parts.append(f"worker={worker_name}")
        if consecutive is not None: parts.append(f"consecutive={consecutive}")
        self._l.log(CIRCUIT, "  ".join(parts))

    def summary(self, name, text):
        short = text[:120] + "..." if len(text) > 120 else text
        self._l.log(SUMMARY_, f"📝  [{name}]  {short}")

    def safety(self, msg, reason=None):
        full = f"🛡  SAFETY  {msg}"
        if reason: full += f"  ({reason})"
        self._l.warning(full)

    def pipeline_start(self, topic):
        self._l.log(SUCCESS, f"\n{'='*60}\n  🚀  PIPELINE START\n  Topic: {topic}\n{'='*60}")

    def pipeline_end(self, total_steps, planner_calls, outcome, workers_done):
        self._l.log(SUCCESS,
            f"\n{'='*60}\n  🏁  PIPELINE END\n"
            f"  Outcome:       {outcome}\n"
            f"  Total steps:   {total_steps}\n"
            f"  Planner calls: {planner_calls}\n"
            f"  Workers done:  {workers_done}\n{'='*60}")


# ── Singleton ─────────────────────────────────────────────────────────────────
log = AgentLogger("research_agent")


def setup_logging(
    log_dir="logs", log_file="agent.log",
    console_level=logging.DEBUG, file_level=logging.DEBUG,
    max_bytes=5*1024*1024, backup_count=3, capture_print=True,
):
    """Configure console + rotating-file logging. Call once at startup."""
    root = logging.getLogger("research_agent")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(console_level)
    ch.setFormatter(_ColourFmt())
    root.addHandler(ch)

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    fh.setLevel(file_level)
    fh.setFormatter(_PlainFmt())
    root.addHandler(fh)

    if capture_print:
        _install_print_capture(root)

    root.log(SUCCESS, f"Logging ready  →  {log_dir}/{log_file}")


_original_print = print

def _install_print_capture(logger):
    import builtins
    def _print(*args, sep=" ", end="\n", file=None, flush=False):
        _original_print(*args, sep=sep, end=end, file=file, flush=flush)
        if file is None:
            msg = sep.join(str(a) for a in args)
            for h in logger.handlers:
                if isinstance(h, logging.handlers.RotatingFileHandler):
                    r = logger.makeRecord(logger.name, logging.DEBUG, "(print)", 0, msg, (), None)
                    h.emit(r)
    builtins.print = _print
