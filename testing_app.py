from pyrogram import Client, filters
from settings import api_id, api_hash


app = Client('my_account', api_id=api_id, api_hash=api_hash)


@app.on_message(filters.private)
async def hello(client, message):
    await message.reply('Hello from Pyrogram!')

app.run()
