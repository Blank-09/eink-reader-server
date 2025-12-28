"""
Modules package for ESP32 Kavita Reader
"""

__version__ = "1.0.0"
from .client import kavita_client, connect_kavita_server

__all__ = ["kavita_client", "connect_kavita_server"]
