# config.py
# Global runtime configuration
IP_COM_DEFAULT_BASE = "192.168.110."   # auto-detect base subnet for IP-COM
IP_COM_SCAN_START = 1
IP_COM_SCAN_END = 254
TIS_PORT = 6000
DISCOVERY_TIMEOUT = 0.6
BUS_DISCOVER_TIMEOUT = 1.0
# Tune concurrency for IP-COM scanning
IP_COM_WORKERS = 50

