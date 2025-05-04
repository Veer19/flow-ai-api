import asyncio
import random
import functools
from openai import RateLimitError, APIConnectionError
from httpx import HTTPStatusError

TRANSIENT_ERRORS = (RateLimitError, APIConnectionError, HTTPStatusError, TimeoutError)

def retry_on_failure(max_attempts=3, base_delay=0.5, max_delay=4):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except TRANSIENT_ERRORS as e:
                    if attempt == max_attempts - 1:
                        raise  # Let it fail after final attempt
                    delay = min(max_delay, base_delay * 2 ** attempt + random.uniform(0, 0.3))
                    print(f"[retry] {fn.__name__} failed ({e}), retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
