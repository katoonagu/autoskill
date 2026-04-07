import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.instagram_brand_search.runners.run_following_only import main


if __name__ == "__main__":
    asyncio.run(main())
