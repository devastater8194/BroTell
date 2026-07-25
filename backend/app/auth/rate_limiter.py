from fastapi import Request, HTTPException, status, Depends
from app.services.redis_service import RedisService
from app.config import settings
from app.auth.auth_handler import get_current_user
from app.models.models import User
from typing import Optional

def rate_limit(limit_override: Optional[int] = None):
  """
  FastAPI dependency builder to enforce sliding window rate limiting.
  If limit_override is specified, it sets a custom per-minute threshold.
  """
  def rate_limiter_dependency(request: Request, user: Optional[User] = Depends(get_current_user)):
    # 1. Identify requester (User ID or client IP)
    if user:
      identifier = f"user:{user.id}"
      limit = limit_override if limit_override is not None else settings.RATE_LIMIT_PER_MINUTE * 3
    else:
      ip = request.client.host if request.client else "unknown_ip"
      identifier = f"ip:{ip}"
      limit = limit_override if limit_override is not None else settings.RATE_LIMIT_PER_MINUTE

    # 2. Build Redis sorted-set key per requester path
    path = request.url.path
    rate_limit_key = f"rate_limit:{identifier}:{path}"

    # 3. Check rate limit
    allowed = RedisService.check_rate_limit(rate_limit_key, limit=limit, period=60)
    if not allowed:
      raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Rate limit exceeded. Please wait a minute and try again."
      )
  return rate_limiter_dependency
