"""
Allow running SyncIndex as a module: python -m syncindex
"""

from .cli import main
import sys

sys.exit(main())
