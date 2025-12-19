import logging
import sys
from contextlib import asynccontextmanager
from bot import bot, dp
from fastapi import FastAPI, Request


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://your-domain.com{WEBHOOK_PATH}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"{bot} webhook set")

    yield

    await bot.delete_webhook()
    logging.info(f"{bot} webhook deleted")


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    await dp.feed_webhook_update(bot, data)
    return {"ok": True}
