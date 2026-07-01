#!/usr/bin/env python3
"""Entry point for the book classification pipeline."""

import asyncio
import sys
from app.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[interrupted] Pipeline stopped by user. Progress has been saved.")
        sys.exit(0)