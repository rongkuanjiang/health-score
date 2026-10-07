"""Vercel Python function; all routes reuse the local dashboard's scoring adapter."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hosted_dashboard import HostedHandler

handler = HostedHandler
