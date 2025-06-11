import hashlib
import json
from functools import wraps
from typing import Callable
import inspect

def make_cache_key(prefix: str, args: tuple, kwargs: dict):
    call_args = args[1:] if len(args) > 0 else args
    raw = f"{prefix}: {json.dumps({'args': call_args, 'kwargs': kwargs}, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()

def redis_cache(prefix: str, ttl: int = 60):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self = args[0]
            redis = getattr(self, "redis", None)
            if redis is None:
                raise RuntimeError("Redis client not found on self!")
            cache_key = make_cache_key(prefix, args, kwargs)
            cached = await redis.get(cache_key)
            if cached: return json.loads(cached)
            
            result = await func(*args, **kwargs)
            result_dicts = [item.model_dump() for item in result]
            if result is not None:
                await redis.setex(cache_key, ttl, json.dumps(result_dicts, default=str))
            return result
        return wrapper
    return decorator