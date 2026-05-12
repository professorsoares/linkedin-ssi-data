import webbrowser
from pathlib import Path


ROOT = Path(__file__).parent

webbrowser.open((ROOT / "dashboard.html").as_uri())