# pylint: skip-file

import sys

if sys.platform == "brython":
    from .brython.typing import *
else:
    from typing import *
