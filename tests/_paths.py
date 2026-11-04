"""Make the engine importable from the tests without installing it."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")
EXAMPLES = os.path.join(ROOT, "examples")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)
os.environ["SHOWRUNNER_NO_PACKS"] = "1"  # tests see the shipped data; the pack tests switch this off themselves
