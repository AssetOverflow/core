"""Run the CLOSE derived climb yardstick.

python -m evals.close_derived_climb
"""

from evals.close_derived_climb.runner import run
import pprint
pprint.pprint(run())