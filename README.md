# rocket_program

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: repository](https://img.shields.io/badge/repository-rocket__program-181717?logo=github)](https://github.com/dragonheart8787/rocket_program)

**Modular Python toolkit for conceptual rocket / launch-vehicle design and engineering analysis** — mission ΔV & staging, propulsion cycles, structures, thermal & TPS, gravity-turn GNC, exterior & engine geometry (JSON/SVG), **V&V**, **uncertainty / sensitivity**, benchmark packs (CEA / GMAT / Sutton–Graves style checks), pluggable aero & surrogate pipelines.

> **Keywords:** `rocket`, `aerospace`, `launch-vehicle`, `propulsion`, `trajectory`, `GNC`, `thermal`, `structures`, `V&V`, `verification`, `validation`, `UQ`, `Monte Carlo`, `sensitivity`, `aerodynamics`, `MDO`, `systems engineering`, `LEO`, `RocketCEA`, `Python`, `NumPy`

繁體中文：**火箭／運載器概念設計與工程分析**（任務、推進、結構、熱力、導引、外觀與引擎生成、驗證確認、不確定度、對標與氣動代理）。

---

## Repository layout

| Path | Purpose |
|------|---------|
| [`rocket_program/`](rocket_program/) | Core Python package (all library modules) |
| [`scripts/`](scripts/) | Thin entrypoints (`run_complete.py`, `run_design_example.py`) |
| [`docs/`](docs/) | Extended documentation & engineering notes |
| [`data/`](data/) | Benchmark / aero sample data |
| [`pyproject.toml`](pyproject.toml) | Package metadata, dependencies, PyPI-oriented keywords |
| [`LICENSE`](LICENSE) | MIT License |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history (align with Git **tags**, e.g. `v1.0.0`) |

Generated outputs (when you run the tools) typically land in the repo root or `full_design_output/`, e.g. `V_V_Report_v1.0.*`, `UQ_Sensitivity_Report_v1.0.json`, `整合工程報告.md`.

---

## Quick start

```bash
# Clone
git clone https://github.com/dragonheart8787/rocket_program.git
cd rocket_program

# Editable install (recommended)
pip install -e .

# Or: run without install (repo root on PYTHONPATH via scripts)
python scripts/run_design_example.py    # design + report
python scripts/run_complete.py          # design + V&V/UQ/repro pack + summary report
```

Optional extras (see `pyproject.toml`):

```bash
pip install -e ".[cea,optuna,salib]"
```

---

## GitHub: description, topics, releases, packages, tags

Repository **description**, **Topics**, **Releases**, and **Tags** are configured on GitHub (not only in Git files). See **[`.github/GITHUB_SETUP.md`](.github/GITHUB_SETUP.md)** for copy-paste text and step-by-step notes.

- Push a version tag: `git tag -a v1.0.0 -m "Release v1.0.0" && git push origin v1.0.0`
- Optional: workflow [`.github/workflows/release.yml`](.github/workflows/release.yml) creates a **Release** when you push `v*.*.*` tags.

---

## Documentation index

- Design generator overview: [`docs/ROCKET_DESIGN_README.md`](docs/ROCKET_DESIGN_README.md)
- TRL4 / benchmarks roadmap: [`docs/TRL4_ROADMAP.md`](docs/TRL4_ROADMAP.md)
- SAP / delivery notes: [`docs/SAP_DELIVERY_SPEC.md`](docs/SAP_DELIVERY_SPEC.md)
- More notes: everything under [`docs/`](docs/)

---

## License

[MIT](LICENSE) — Copyright (c) 2026 dragonheart8787.
