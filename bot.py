import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.future import select
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from settings import api_id, api_hash
from database import SessionLocal, init_db
from models import User, Message, Base


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
private_filter = filters.create(lambda _, __,
                                message: message.chat.type == 'private')

app = Client('my_account', api_id=api_id, api_hash=api_hash)


async def send_message(client, user_id, message_text):
    try:
        await client.send_message(user_id, message_text)
        logger.info(f'Отправлено сообщение пользователю user_id={user_id}: {message_text}')
    except FloodWait as e:
        logger.warning(f'FloodWait: Пауза на {e.x} секунд')
        await asyncio.sleep(e.x)
    except Exception as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')

@app.on_message(private_filter)
async def handle_message(client, message):
    logger.info('Вызван handle_message')
    logger.info(f'Получено сообщение от user_id={message.from_user.id}: {message.text}')

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(User).filter_by(id=message.from_user.id))
            user = result.scalars().first()

            if not user:
                new_user = User(id=message.from_user.id, username=message.from_user.username)
                session.add(new_user)
                await session.commit()
                logger.info(f'Добавлен новый пользователь в базу данных: {new_user}')

                await add_message(session, new_user.id, 'Текст1',
                                  timedelta(minutes=2))
                await add_message(session, new_user.id, 'Текст2',
                                  timedelta(minutes=3), trigger='Триггер1',
                                  reference_message_id=1)
                await add_message(session, new_user.id, 'Текст3',
                                  timedelta(days=1, hours=2),
                                  reference_message_id=2)
            else:
                logger.info(f'Пользователь уже существует: {user}')

    await check_and_send_messages()


async def add_message(session, user_id, message_text, delay, trigger=None,
                      reference_message_id=None):
    scheduled_time = datetime.utcnow() + delay
    async with session.begin():
        new_message = Message(user_id=user_id, message_text=message_text, scheduled_time=scheduled_time, trigger=trigger, reference_message_id=reference_message_id)
        session.add(new_message)
        await session.commit()
        logger.info(f'Запланировано сообщение для user_id={user_id} на {scheduled_time}: {message_text}')


async def check_and_send_messages():
    current_time_utc = datetime.utcnow()
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Message).where(Message.sent.is_(False), Message.scheduled_time <= current_time_utc))
            messages = result.scalars().all()
            for message in messages:
                if message.trigger:
                    incoming_messages = await app.get_messages('@mandreykin')
                    if any(message.trigger in msg.text for msg in incoming_messages):
                        logger.info(f'Сообщение для user_id={message.user_id} отменено из-за триггера: {message.trigger}')
                        continue
                await send_message(app, message.user_id, message.message_text)
                message.sent = True
                session.add(message)
            await session.commit()


async def main():
    try:
        await init_db()
        await app.start()
        logger.info('Бот запущен')

        try:
            await check_and_send_messages()
            while True:
                await asyncio.sleep(60)
                try:
                    await check_and_send_messages()
                except Exception as e:
                    logger.error(f'Ошибка во время проверки и отправки сообщений: {e}')
        finally:
            await app.stop()
            logger.info('Бот остановлен')
    except Exception as e:
        logger.error(f'Unhandled exception in main(): {e}')
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Принудительная остановка бота по запросу пользователя')
