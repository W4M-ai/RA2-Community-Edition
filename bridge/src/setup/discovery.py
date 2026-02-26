from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = "/app/.discovered_repeater"
LUTRON_DEFAULT_PORT = 23
SCAN_TIMEOUT = 2.0
HANDSHAKE_TIMEOUT = 3.0


async def discover_repeater(
    port: int = LUTRON_DEFAULT_PORT,
    cache_path: str = DEFAULT_CACHE_PATH,
) -> str | None:
    """Auto-discover a Lutron RA2 repeater on the local network.

    Returns the IP address if found, None otherwise.
    Checks cache first, then scans the network.
    """
    # Try cached IP first
    cached = _read_cache(cache_path)
    if cached:
        logger.info("Trying cached repeater at %s", cached)
        if await _verify_repeater(cached, port):
            return cached
        logger.info("Cached repeater at %s not responding, re-scanning", cached)

    logger.info("Scanning for RA2 repeater...")

    # Strategy 1: Check ARP/neighbor table
    candidates = await _get_arp_hosts()
    if candidates:
        logger.info("Checking %d known hosts from ARP table", len(candidates))
        result = await _scan_candidates(candidates, port)
        if result:
            _write_cache(cache_path, result)
            return result

    # Strategy 2: Subnet scan
    subnet = _get_local_subnet()
    if subnet:
        logger.info("Scanning subnet %s.0/24 on port %d", subnet, port)
        all_hosts = [f"{subnet}.{i}" for i in range(1, 255)]
        result = await _scan_candidates(all_hosts, port)
        if result:
            _write_cache(cache_path, result)
            return result

    logger.error("Could not find RA2 repeater on local network.")
    logger.error("Set RA2_HOST in your .env file to the repeater's IP address.")
    return None


async def _verify_repeater(host: str, port: int) -> bool:
    """Verify a host is a Lutron repeater by checking for the login prompt."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=SCAN_TIMEOUT,
        )
        try:
            data = await asyncio.wait_for(
                reader.read(1024),
                timeout=HANDSHAKE_TIMEOUT,
            )
            return b"login" in data.lower()
        finally:
            writer.close()
            await writer.wait_closed()
    except (OSError, asyncio.TimeoutError):
        return False


async def _check_port(host: str, port: int) -> str | None:
    """Check if a host has the given port open."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=SCAN_TIMEOUT,
        )
        writer.close()
        await writer.wait_closed()
        return host
    except (OSError, asyncio.TimeoutError):
        return None


async def _scan_candidates(hosts: list[str], port: int) -> str | None:
    """Scan a list of hosts for open port, then verify the first hit."""
    # Parallel port check
    tasks = [_check_port(host, port) for host in hosts]
    results = await asyncio.gather(*tasks)
    open_hosts = [r for r in results if r is not None]

    # Verify each with LIP handshake
    for host in open_hosts:
        if await _verify_repeater(host, port):
            logger.info("Found RA2 repeater at %s", host)
            return host

    return None


async def _get_arp_hosts() -> list[str]:
    """Get IP addresses from the system ARP/neighbor table."""
    hosts = []

    # Try /proc/net/arp (Linux/Docker)
    arp_path = Path("/proc/net/arp")
    if arp_path.exists():
        try:
            for line in arp_path.read_text().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 4 and parts[2] != "0x0":
                    hosts.append(parts[0])
            return hosts
        except Exception:
            pass

    # Fallback: ip neigh command
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip", "neigh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        for line in stdout.decode().splitlines():
            parts = line.split()
            if parts and parts[-1] != "FAILED":
                hosts.append(parts[0])
    except FileNotFoundError:
        pass

    return hosts


def _get_local_subnet() -> str | None:
    """Get the local /24 subnet prefix (e.g., '192.168.1')."""
    import socket
    try:
        # Connect to a public IP to determine local interface (doesn't send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        parts = local_ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3])
    except Exception:
        pass
    return None


def _read_cache(cache_path: str) -> str | None:
    """Read cached repeater IP."""
    path = Path(cache_path)
    if path.exists():
        ip = path.read_text().strip()
        if ip:
            return ip
    return None


def _write_cache(cache_path: str, ip: str) -> None:
    """Cache discovered repeater IP."""
    try:
        Path(cache_path).write_text(ip)
        logger.info("Cached repeater IP to %s", cache_path)
    except Exception as exc:
        logger.warning("Could not cache repeater IP: %s", exc)
