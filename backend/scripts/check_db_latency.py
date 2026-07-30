import asyncio
import time
from app.core.database import async_session_maker
from sqlalchemy import text

async def check_latency():
    times = []
    async with async_session_maker() as db:
        for i in range(10):
            start = time.time()
            await db.execute(text("SELECT 1"))
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            print(f"Ping {i+1}: {elapsed:.1f}ms")
    
    print(f"\nAvg: {sum(times)/len(times):.1f}ms")
    print(f"Min: {min(times):.1f}ms")
    print(f"Max: {max(times):.1f}ms")

asyncio.run(check_latency())
