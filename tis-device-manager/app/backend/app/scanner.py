# scanner.py
import socket
import asyncio
import concurrent.futures
from typing import List
from app import config, tis_protocol

def probe_ip_for_tis(ip: str, timeout: float = None) -> tuple:
    """Send discovery to single IP and return parsed frame if any."""
    timeout = timeout or config.DISCOVERY_TIMEOUT
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(tis_protocol.DISCOVERY_PACKET, (ip, config.TIS_PORT))
        data, addr = sock.recvfrom(2048)
        if tis_protocol.is_tis_frame(data):
            parsed = tis_protocol.parse_device_info_frame(data)
            parsed["ip"] = addr[0]
            return True, parsed
    except socket.timeout:
        return False, None
    except Exception:
        return False, None
    finally:
        try:
            sock.close()
        except:
            pass
    return False, None

def find_ip_comport_in_range(base_ip: str = None, start: int = None, end: int = None) -> List[str]:
    """Scan range concurrently to find IP-COM(s) that respond with a TIS frame."""
    base = base_ip or config.IP_COM_DEFAULT_BASE
    start = start or config.IP_COM_SCAN_START
    end = end or config.IP_COM_SCAN_END

    ips = [f"{base.rstrip('.')}.{i}" for i in range(start, end + 1)]
    found = []

    # use threadpool to speed up UDP probes
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.IP_COM_WORKERS) as exe:
        futures = {exe.submit(probe_ip_for_tis, ip): ip for ip in ips}
        for fut in concurrent.futures.as_completed(futures):
            try:
                ok, parsed = fut.result()
                if ok:
                    found_ip = parsed.get("ip")
                    if found_ip and found_ip not in found:
                        found.append(found_ip)
            except Exception:
                pass
    return found

def discover_bus_via_ip_com(ip_com_ip: str, timeout: float = None) -> List[dict]:
    """Send one broadcast discovery to IP-COM and collect replies until timeout."""
    timeout = timeout or config.BUS_DISCOVER_TIMEOUT
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    discovered = []
    try:
        sock.sendto(tis_protocol.DISCOVERY_PACKET, (ip_com_ip, config.TIS_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                if tis_protocol.is_tis_frame(data):
                    parsed = tis_protocol.parse_device_info_frame(data)
                    parsed["ip"] = addr[0]
                    parsed["port"] = addr[1]
                    discovered.append(parsed)
            except socket.timeout:
                break
    finally:
        try:
            sock.close()
        except:
            pass

    # dedupe by subnet-device
    unique = {}
    for d in discovered:
        key = (d["subnet"], d["device_id"])
        if key not in unique:
            unique[key] = d
    return list(unique.values())
