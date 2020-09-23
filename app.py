#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedule
import asyncio
import os
import time
import threading
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters

import utils as util
import bot_db as db
import settings


def error(update, context):
    util.logger.warning(f'Update encountered an error "{context.error}"')


def _subscribers_checkpoint():
    db.SubscribersLog.checkpoint(settings.TELEGRAM['channel_id'])


@util.restricted
def insights(update, context):
    stats = util.getDBstats()
    db.SubscribersLog.plot(settings.TELEGRAM['channel_id'])
    update.message.reply_photo(caption=(
        f"Подписчиков: {util.tg_bot.get_chat_members_count(settings.TELEGRAM['channel_id'])}\n"
        f"Постов всего: {stats['total']}\n"
        f"Постов за сутки: {stats['today']}\n"
        f"Прошлый пост был: {stats['last_post'].strftime('%d.%m в %H:%M')}\n"),
        photo=open('subs_plot.png', 'rb')
    )
    os.remove('subs_plot.png')


@util.restricted
def create_index(update, context):
    util.tg_bot.send_message(
        settings.TELEGRAM['sudo_users'][0],
        'Начинаю индексировать...')
    thread = threading.Thread(target=util.index_images)
    thread.start()


@util.restricted
def post_now(update, context):
    util.post_to_telegram()
    update.message.reply_text('Запостили постик')


def button(update, context):
    query = update.callback_query
    query.answer()

    qdata = query.data.split('-')

    if(qdata[0] == 'like'):
        picture = db.Picture.where(post_id=query.message.message_id).one()
        db.Likes.like(
            user_id=update.effective_user.id,
            post_id=query.message.message_id,
            media_id=picture.id)

        util.update_like_button(
            query.message.chat_id, query.message.message_id)


def image_handler(update, context):
    file = util.tg_bot.getFile(update.message.photo[-1].file_id)
    path = os.path.join(settings.IMAGES_PATH, f'{int(time.time())}.jpg')
    file.download(path)
    db.Picture.addToIndex(filename=path)
    update.message.reply_text('Добавлено в индекс')


async def start_scheduling():
    (schedule.every(settings.POSTING_RATE_MIN)
        .to(settings.POSTING_RATE_MAX)
        .minutes.do(util.post_to_telegram))

    schedule.every().day.at('12:30').do(_subscribers_checkpoint)

    print('Started scheduling')
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


async def start_polling():
    updater = Updater(
        bot=util.tg_bot,
        request_kwargs={
            'read_timeout': 1000, 'connect_timeout': 1000,
            'pool_connections': 100, 'pool_maxsize': 100},
        use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("insights", insights))
    dp.add_handler(CommandHandler("index", create_index))
    dp.add_handler(CommandHandler("postnow", post_now))
    dp.add_handler(MessageHandler(Filters.photo, image_handler))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_error_handler(error)
    print('Started polling')
    updater.start_polling()


def main():
    loop = asyncio.get_event_loop()

    try:
        loop.create_task(start_polling())
        loop.create_task(start_scheduling())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("Quitting...")
        loop.close()


if __name__ == '__main__':
    main()
