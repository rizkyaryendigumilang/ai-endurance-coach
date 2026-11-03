import time
from typing import Dict, Tuple, List
from fastapi import HTTPException, Request

class TokenBucketRateLimiter:
    """
    Lightweight, thread-safe in-memory token bucket rate limiter with TTL eviction
    and reverse-proxy (X-Forwarded-For) real client IP resolution.
    Prevents API quota drainage (Google Gemini & OpenAI) and DDoS attempts.
    """
    def __init__(self, rate_per_minute: int = 20, burst: int = 5, max_entries: int = 5000, ttl_seconds: int = 600):
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = burst + rate_per_minute
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.buckets: Dict[str, Tuple[float, float]] = {}  # ip -> (tokens, last_updated)
        self.last_cleanup = time.time()

    def get_client_ip(self, request: Request) -> str:
        """Resolve true client IP even when situated behind Reverse Proxy (Nginx, Cloudflare)."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "127.0.0.1"

    def _prune_expired(self, now: float):
        """Evict stale bucket records older than ttl_seconds."""
        expired: List[str] = [ip for ip, (_, last_up) in self.buckets.items() if now - last_up > self.ttl_seconds]
        for ip in expired:
            del self.buckets[ip]

    def check(self, request: Request, cost: int = 1):
        now = time.time()

        # Periodic housekeeping every 60 seconds
        if now - self.last_cleanup > 60:
            if len(self.buckets) > 100:
                self._prune_expired(now)
            self.last_cleanup = now

        # Memory limit guard: evict oldest 20% if max capacity exceeded
        if len(self.buckets) >= self.max_entries:
            self._prune_expired(now)
            if len(self.buckets) >= self.max_entries:
                sorted_by_time = sorted(self.buckets.items(), key=lambda item: item[1][1])
                for ip, _ in sorted_by_time[:int(self.max_entries * 0.2)]:
                    del self.buckets[ip]

        client_ip = self.get_client_ip(request)

        if client_ip not in self.buckets:
            self.buckets[client_ip] = (self.capacity - cost, now)
            return True

        tokens, last_updated = self.buckets[client_ip]
        # Replenish tokens based on elapsed time
        elapsed = now - last_updated
        tokens = min(self.capacity, tokens + (elapsed * self.rate_per_second))

        if tokens >= cost:
            self.buckets[client_ip] = (tokens - cost, now)
            return True
        else:
            retry_after = int((cost - tokens) / self.rate_per_second) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Batas permintaan AI Coach tercapai (Rate Limit). Coba lagi dalam {retry_after} detik.",
                headers={"Retry-After": str(retry_after)}
            )

# Global rate limiters
chat_rate_limiter = TokenBucketRateLimiter(rate_per_minute=20, burst=5)
vision_rate_limiter = TokenBucketRateLimiter(rate_per_minute=10, burst=3)
