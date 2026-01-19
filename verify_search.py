
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fma.tools.pipeline_tools import get_md_files
from fma.config import FMAConfig

print(f"Searching in directory: {FMAConfig.MD_DIRECTORY}")
files = get_md_files()
print(f"Found {len(files)} markdown files.")
for f in files[:5]:
    print(f" - {os.path.basename(f)}")
if len(files) > 5:
    print(f" ... and {len(files) - 5} more.")
