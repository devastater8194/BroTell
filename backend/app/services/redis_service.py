import time
import json
from typing import Optional, Union, Any
from app.config import settings

# Attempt to import redis
try:
  import redis
  REDIS_AVAILABLE = True
except ImportError:
  REDIS_AVAILABLE = False

class MockRedis:
  """Fallback mock Redis client for development environment when Redis is not running."""
  def __init__(self):
    self._store = {}
    self._ttls = {}
    self._zsets = {}

  def get(self, key: str) -> Optional[str]:
    now = time.time()
    if key in self._ttls and self._ttls[key] < now:
      self.delete(key)
      return None
    return self._store.get(key)

  def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
    self._store[key] = value
    if ex:
      self._ttls[key] = time.time() + ex
    elif key in self._ttls:
      del self._ttls[key]
    return True

  def delete(self, key: str) -> bool:
    if key in self._store:
      del self._store[key]
    if key in self._ttls:
      del self._ttls[key]
    if key in self._zsets:
      del self._zsets[key]
    return True

  def exists(self, key: str) -> int:
    return 1 if self.get(key) is not None else 0

  def pipeline(self):
    return MockPipeline(self)

class MockPipeline:
  def __init__(self, client):
    self.client = client
    self.commands = []

  def zadd(self, key: str, mapping: dict):
    self.commands.append(("zadd", key, mapping))
    return self

  def zremrangebyscore(self, key: str, min_val: float, max_val: float):
    self.commands.append(("zremrangebyscore", key, min_val, max_val))
    return self

  def zcard(self, key: str):
    self.commands.append(("zcard", key))
    return self

  def expire(self, key: str, ttl: int):
    self.commands.append(("expire", key, ttl))
    return self

  def execute(self):
    results = []
    now = time.time()
    for cmd in self.commands:
      op = cmd[0]
      if op == "zadd":
        key, mapping = cmd[1], cmd[2]
        if key not in self.client._zsets:
          self.client._zsets[key] = []
        for val, score in mapping.items():
          self.client._zsets[key].append((score, val))
        results.append(len(mapping))
      elif op == "zremrangebyscore":
        key, min_val, max_val = cmd[1], cmd[2], cmd[3]
        if key in self.client._zsets:
          original_len = len(self.client._zsets[key])
          self.client._zsets[key] = [item for item in self.client._zsets[key] if not (min_val <= item[0] <= max_val)]
          results.append(original_len - len(self.client._zsets[key]))
        else:
          results.append(0)
      elif op == "zcard":
        key = cmd[1]
        results.append(len(self.client._zsets.get(key, [])))
      elif op == "expire":
        results.append(True)
    self.commands = []
    return results

class RedisService:
  _client: Optional[Union[redis.Redis, MockRedis]] = None
  _use_mock: bool = False

  @classmethod
  def get_client(cls):
    if cls._client is not None:
      return cls._client

    if not REDIS_AVAILABLE:
      print("RedisService: redis library not installed. Falling back to Mock in-memory caching.")
      cls._client = MockRedis()
      cls._use_mock = True
      return cls._client

    try:
      print(f"RedisService: Connecting to Redis at {settings.REDIS_URL}...")
      cls._client = redis.Redis.from_url(
        settings.REDIS_URL, 
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0
      )
      # Ping to test connection viability
      cls._client.ping()
      print("RedisService: Connection established successfully.")
    except Exception as e:
      print(f"RedisService: Failed to connect to Redis ({type(e).__name__}: {e}). Falling back to Mock in-memory caching.")
      cls._client = MockRedis()
      cls._use_mock = True

    return cls._client

  @classmethod
  def get(cls, key: str) -> Optional[str]:
    try:
      return cls.get_client().get(key)
    except Exception as e:
      print(f"RedisService Error (get): {e}")
      return None

  @classmethod
  def set(cls, key: str, value: str, ex: Optional[int] = None) -> bool:
    try:
      return cls.get_client().set(key, value, ex=ex)
    except Exception as e:
      print(f"RedisService Error (set): {e}")
      return False

  @classmethod
  def delete(cls, key: str) -> bool:
    try:
      return bool(cls.get_client().delete(key))
    except Exception as e:
      print(f"RedisService Error (delete): {e}")
      return False

  @classmethod
  def exists(cls, key: str) -> bool:
    try:
      return bool(cls.get_client().exists(key))
    except Exception as e:
      print(f"RedisService Error (exists): {e}")
      return False

  @classmethod
  def check_rate_limit(cls, key: str, limit: int, period: int = 60) -> bool:
    """
    Sliding window rate limiting using Redis Sorted Sets.
    Returns:
      True if request is ALLOWED (not rate limited)
      False if request is BLOCKED (rate limited)
    """
    try:
      client = cls.get_client()
      now = time.time()
      now_ms = str(now * 1000) # Unique member identifier
      
      pipe = client.pipeline()
      # Add item to sorted set
      pipe.zadd(key, {now_ms: now})
      # Remove elements older than (now - period)
      pipe.zremrangebyscore(key, 0, now - period)
      # Count elements in sliding window
      pipe.zcard(key)
      # Set key expiration to prevent leak
      pipe.expire(key, period)
      
      results = pipe.execute()
      count = results[2] # ZCARD result index
      
      if count > limit:
        return False
      return True
    except Exception as e:
      # If Redis rate limiting fails, fail open to avoid service outage, but log
      print(f"RedisService Rate Limiter Exception (fail-open): {e}")
      return True

  @classmethod
  def get_video_cache(cls, video_id: str, key_suffix: str) -> Optional[dict]:
    """Retrieves video level structured cache."""
    val = cls.get(f"video:{video_id}:{key_suffix}")
    if val:
      try:
        return json.loads(val)
      except Exception:
        return None
    return None

  @classmethod
  def set_video_cache(cls, video_id: str, key_suffix: str, value: Any, ttl: int = 86400) -> bool:
    """Saves video level structured cache with TTL."""
    try:
      return cls.set(f"video:{video_id}:{key_suffix}", json.dumps(value), ex=ttl)
    except Exception:
      return False

  @classmethod
  def publish(cls, channel: str, message: str):
    """Publishes streaming token/message over Redis Pub/Sub."""
    try:
      client = cls.get_client()
      if not cls._use_mock:
        client.publish(channel, message)
    except Exception as e:
      print(f"RedisService Pub/Sub publish error: {e}")

  @classmethod
  def get_task_lock(cls, lock_name: str) -> Optional[str]:
    """Retrieves the Celery job ID of a running task lock, if it exists."""
    return cls.get(f"lock:task:{lock_name}")

  @classmethod
  def set_task_lock(cls, lock_name: str, job_id: str, ttl: int = 600) -> bool:
    """Sets a task lock to the given Celery job ID with a TTL."""
    return cls.set(f"lock:task:{lock_name}", job_id, ex=ttl)

  @classmethod
  def release_task_lock(cls, lock_name: str) -> bool:
    """Releases a task lock."""
    return cls.delete(f"lock:task:{lock_name}")
