#!/usr/bin/env python3
"""Command-line entry point for the Section 508 Compliance Checker.

This thin wrapper delegates to :func:`section508checker.cli.main` so the tool
can be invoked as ``python checker.py`` while the implementation lives in an
importable, testable package.
"""

import sys

from section508checker.cli import main

if __name__ == "__main__":
    sys.exit(main())
