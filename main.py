#!/usr/bin/env python3
"""Punto de entrada de IVI."""
from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el paquete ivi sea importable cuando se ejecuta como script
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ivi.app import IVIApp


def main() -> int:
    app = IVIApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
