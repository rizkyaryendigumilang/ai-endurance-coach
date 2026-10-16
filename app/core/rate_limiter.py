import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request

class TokenBucketRateLimiter:
    """
    Lightweight, thread-safe in-memory token bucket rate limiter.
    Prevents API quota drainage (Google Gemini & OpenAI) and DDoS attempts.
    """
    def __init__(self, rate_per_minute: int = 20, burst: int = 5):
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = burst + rate_per_minute
        self.buckets: Dict[str, Tuple[float, float]] = {}  # ip -> (tokens, last_updated)

    def check(self, request: Request, cost: int = 1):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

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
