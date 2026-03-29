# -*- coding: utf-8 -*-
"""TRL4 升級一鍵腳本（Benchmark + 氣動 + Surrogate + Real Aero V&V）"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from rocket_program.run_tr14_upgrade import main

if __name__ == "__main__":
    main()
