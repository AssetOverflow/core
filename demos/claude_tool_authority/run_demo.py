"""Run the frontier-proposer-to-CORE tool-authority demo.

Each fixture is evaluated twice.  The run fails if any scenario drifts from its
committed expected artifact or if the two executions differ byte-for-byte.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path