import asyncio
from telegram import Bot

async def limpar_webhook():
    bot = Bot("7680606076:AAFVfNAKU-jP_pWb9ZGuvL1DoRu8vYMPS48")  # substitua pelo token real
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deletado com sucesso!")

asyncio.run(limpar_webhook())
