"""Print the Python version and the version of every package TraceCheck needs."""

import importlib
import sys

PACKAGES = ["streamlit", "pandas", "pydantic", "openpyxl", "reportlab", "PIL", "yaml", "pytest"]

print(f"Python {sys.version.split()[0]}")
if sys.version_info < (3, 11):
    print("  WARNING: Python 3.11 or newer is recommended.")

missing = []
for name in PACKAGES:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", None) or getattr(module, "Version", "unknown")
        print(f"  {name:10s} {version}")
    except ImportError:
        print(f"  {name:10s} MISSING")
        missing.append(name)

if missing:
    print("Missing packages. Run: pip install -r requirements.txt")
    sys.exit(1)
print("Environment OK.")
