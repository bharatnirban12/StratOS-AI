import asyncio
import random


async def retry_async(func, retries=3, delay=2, backoff=2):
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            if attempt == retries - 1:
                raise 
            jitter = random.uniform(0, 1)

            await asyncio.sleep(
                (delay * backoff ** attempt)
                + jitter
            )