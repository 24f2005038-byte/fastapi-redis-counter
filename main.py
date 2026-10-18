import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from redis.exceptions import RedisError


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.environ.get("REDIS_URL")

    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is required")

    app.state.redis = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )

    try:
        await app.state.redis.ping()
        yield
    finally:
        await app.state.redis.aclose()


app = FastAPI(
    title="FastAPI Redis Counter",
    version="1.0.0",
    lifespan=lifespan,
)


def get_redis():
    return app.state.redis


@app.get("/healthz")
async def healthz():
    try:
        await get_redis().ping()
        return {"status": "ok", "redis": "up"}
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "redis": "down"},
        )


@app.post("/hit/{key}")
async def hit(key: str):
    try:
        count = await get_redis().incr(f"counter:{key}")
        return {"key": key, "count": count}
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/count/{key}")
async def count(key: str):
    try:
        value = await get_redis().get(f"counter:{key}")
        return {"key": key, "count": int(value) if value is not None else 0}
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")
