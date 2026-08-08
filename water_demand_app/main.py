#!/usr/bin/env python3
"""Water Demand Report Generator - Production Entry Point."""

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from ui.app import run_app

if __name__ == "__main__":
    run_app()
