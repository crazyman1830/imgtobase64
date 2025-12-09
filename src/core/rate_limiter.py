"""
Rate limiting module for the image base64 converter.

This module provides IP-based rate limiting functionality to protect
against abuse and ensure fair usage of the service.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..models.models import RateLimitExceededError


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10  # Maximum requests in a short burst
    burst_window: int = 10  # Burst window in seconds
    cleanup_interval: int = 300  # Cleanup old entries every 5 minutes


@dataclass
class RateLimitStatus:
    """Status information for rate limiting."""

    ip_address: str
    requests_in_minute: int
    requests_in_hour: int
    requests_in_day: int
    requests_in_burst: int
    is_limited: bool
    reset_time: float
    remaining_requests: int


class RateLimiter:
    """
    IP-based rate limiter with multiple time windows.

    Provides rate limiting based on requests per minute, hour, and day,
    with additional burst protection and automatic cleanup of old entries.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize the rate limiter.

        Args:
            config: Rate limiting configuration (uses default if None)
        """
        self.config = config or RateLimitConfig()

        # Thread-safe storage for request tracking
        self._lock = threading.RLock()

        # Track requests by IP address and time window
        self._minute_requests: Dict[str, deque] = defaultdict(deque)
        self._hour_requests: Dict[str, deque] = defaultdict(deque)
        self._day_requests: Dict[str, deque] = defaultdict(deque)
        self._burst_requests: Dict[str, deque] = defaultdict(deque)

        # Track when each IP was last seen for cleanup
        self._last_seen: Dict[str, float] = {}

        # Last cleanup time
        self._last_cleanup = time.time()

        # Logger for rate limiting events
        self.logger = logging.getLogger(__name__)

    def check_rate_limit(
        self, ip_address: str, raise_on_limit: bool = True
    ) -> RateLimitStatus:
        """
        Check if an IP address is within rate limits.

        Args:
            ip_address: IP address to check
            raise_on_limit: Whether to raise exception if limit exceeded

        Returns:
            RateLimitStatus: Current rate limit status

        Raises:
            RateLimitExceededError: If rate limit exceeded and raise_on_limit is True
        """
        with self._lock:
            current_time = time.time()

            # Perform cleanup if needed
            self._cleanup_old_entries(current_time)

            # Update last seen time
            self._last_seen[ip_address] = current_time

            # Clean up old requests for this IP
            self._cleanup_ip_requests(ip_address, current_time)

            # Count current requests in each time window
            minute_count = len(self._minute_requests[ip_address])
            hour_count = len(self._hour_requests[ip_address])
            day_count = len(self._day_requests[ip_address])
            burst_count = len(self._burst_requests[ip_address])

            # Check limits
            is_limited = (
                minute_count >= self.config.requests_per_minute
                or hour_count >= self.config.requests_per_hour
                or day_count >= self.config.requests_per_day
                or burst_count >= self.config.burst_limit
            )

            # Calculate reset time (next minute boundary)
            reset_time = (int(current_time / 60) + 1) * 60

            # Calculate remaining requests (most restrictive limit)
            remaining_minute = max(0, self.config.requests_per_minute - minute_count)
            remaining_hour = max(0, self.config.requests_per_hour - hour_count)
            remaining_day = max(0, self.config.requests_per_day - day_count)
            remaining_burst = max(0, self.config.burst_limit - burst_count)

            remaining_requests = min(
                remaining_minute, remaining_hour, remaining_day, remaining_burst
            )

            status = RateLimitStatus(
                ip_address=ip_address,
                requests_in_minute=minute_count,
                requests_in_hour=hour_count,
                requests_in_day=day_count,
                requests_in_burst=burst_count,
                is_limited=is_limited,
                reset_time=reset_time,
                remaining_requests=remaining_requests,
            )

            if is_limited:
                # Log rate limit violation
                self.logger.warning(
                    f"Rate limit exceeded for IP {ip_address}: "
                    f"minute={minute_count}/{self.config.requests_per_minute}, "
                    f"hour={hour_count}/{self.config.requests_per_hour}, "
                    f"day={day_count}/{self.config.requests_per_day}, "
                    f"burst={burst_count}/{self.config.burst_limit}"
                )

                if raise_on_limit:
                    raise RateLimitExceededError(
                        f"Rate limit exceeded for IP {ip_address}. "
                        f"Try again in {int(reset_time - current_time)} seconds."
                    )

            return status

    def record_request(self, ip_address: str) -> RateLimitStatus:
        """
        Record a request from an IP address.

        Args:
            ip_address: IP address making the request

        Returns:
            RateLimitStatus: Updated rate limit status

        Raises:
            RateLimitExceededError: If rate limit would be exceeded
        """
        # First check if request is allowed
        status = self.check_rate_limit(ip_address, raise_on_limit=True)

        with self._lock:
            current_time = time.time()

            # Record the request in all time windows
            self._minute_requests[ip_address].append(current_time)
            self._hour_requests[ip_address].append(current_time)
            self._day_requests[ip_address].append(current_time)
            self._burst_requests[ip_address].append(current_time)

            # Update last seen time
            self._last_seen[ip_address] = current_time

            # Return updated status
            return self.check_rate_limit(ip_address, raise_on_limit=False)

    def _cleanup_ip_requests(self, ip_address: str, current_time: float) -> None:
        """
        Clean up old requests for a specific IP address.

        Args:
            ip_address: IP address to clean up
            current_time: Current timestamp
        """
        # Clean up minute requests (older than 60 seconds)
        minute_cutoff = current_time - 60
        while (
            self._minute_requests[ip_address]
            and self._minute_requests[ip_address][0] < minute_cutoff
        ):
            self._minute_requests[ip_address].popleft()

        # Clean up hour requests (older than 3600 seconds)
        hour_cutoff = current_time - 3600
        while (
            self._hour_requests[ip_address]
            and self._hour_requests[ip_address][0] < hour_cutoff
        ):
            self._hour_requests[ip_address].popleft()

        # Clean up day requests (older than 86400 seconds)
        day_cutoff = current_time - 86400
        while (
            self._day_requests[ip_address]
            and self._day_requests[ip_address][0] < day_cutoff
        ):
            self._day_requests[ip_address].popleft()

        # Clean up burst requests (older than burst window)
        burst_cutoff = current_time - self.config.burst_window
        while (
            self._burst_requests[ip_address]
            and self._burst_requests[ip_address][0] < burst_cutoff
        ):
            self._burst_requests[ip_address].popleft()

    def _cleanup_old_entries(self, current_time: float) -> None:
        """
        Clean up old entries to prevent memory leaks.

        Args:
            current_time: Current timestamp
        """
        # Only cleanup periodically
        if current_time - self._last_cleanup < self.config.cleanup_interval:
            return

        self._last_cleanup = current_time

        # Find IPs that haven't been seen for more than a day
        cleanup_cutoff = current_time - 86400  # 24 hours
        ips_to_remove = [
            ip
            for ip, last_seen in self._last_seen.items()
            if last_seen < cleanup_cutoff
        ]

        # Remove old IP entries
        for ip in ips_to_remove:
            self._minute_requests.pop(ip, None)
            self._hour_requests.pop(ip, None)
            self._day_requests.pop(ip, None)
            self._burst_requests.pop(ip, None)
            self._last_seen.pop(ip, None)

        if ips_to_remove:
            self.logger.info(
                f"Cleaned up rate limit data for {len(ips_to_remove)} old IPs"
            )

    def get_status(self, ip_address: str) -> RateLimitStatus:
        """
        Get current rate limit status for an IP address without recording a request.

        Args:
            ip_address: IP address to check

        Returns:
            RateLimitStatus: Current status
        """
        return self.check_rate_limit(ip_address, raise_on_limit=False)

    def reset_ip(self, ip_address: str) -> None:
        """
        Reset rate limit counters for a specific IP address.

        Args:
            ip_address: IP address to reset
        """
        with self._lock:
            self._minute_requests.pop(ip_address, None)
            self._hour_requests.pop(ip_address, None)
            self._day_requests.pop(ip_address, None)
            self._burst_requests.pop(ip_address, None)
            self._last_seen.pop(ip_address, None)

            self.logger.info(f"Reset rate limit counters for IP {ip_address}")

    def get_all_statuses(self) -> Dict[str, RateLimitStatus]:
        """
        Get rate limit status for all tracked IP addresses.

        Returns:
            dict: Mapping of IP addresses to their status
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_entries(current_time)

            statuses = {}
            for ip in list(self._last_seen.keys()):
                try:
                    statuses[ip] = self.get_status(ip)
                except Exception as e:
                    self.logger.error(f"Error getting status for IP {ip}: {e}")

            return statuses

    def update_config(self, config: RateLimitConfig) -> None:
        """
        Update rate limiting configuration.

        Args:
            config: New configuration
        """
        with self._lock:
            self.config = config
            self.logger.info(f"Updated rate limit configuration: {config}")

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the rate limiter.

        Returns:
            dict: Statistics including number of tracked IPs, total requests, etc.
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_entries(current_time)

            total_ips = len(self._last_seen)
            total_minute_requests = sum(
                len(reqs) for reqs in self._minute_requests.values()
            )
            total_hour_requests = sum(
                len(reqs) for reqs in self._hour_requests.values()
            )
            total_day_requests = sum(len(reqs) for reqs in self._day_requests.values())

            return {
                "tracked_ips": total_ips,
                "requests_last_minute": total_minute_requests,
                "requests_last_hour": total_hour_requests,
                "requests_last_day": total_day_requests,
                "config": {
                    "requests_per_minute": self.config.requests_per_minute,
                    "requests_per_hour": self.config.requests_per_hour,
                    "requests_per_day": self.config.requests_per_day,
                    "burst_limit": self.config.burst_limit,
                    "burst_window": self.config.burst_window,
                },
            }


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.

    Returns:
        RateLimiter: Global rate limiter instance
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def configure_rate_limiter(config: RateLimitConfig) -> None:
    """
    Configure the global rate limiter.

    Args:
        config: Rate limiting configuration
    """
    limiter = get_rate_limiter()
    limiter.update_config(config)
