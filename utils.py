#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib
import logging
import json
import secrets
from functools import wraps
import multiprocessing.dummy as mp
from telegram import Bot, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color

import bot_db as db
import settings


# Enable logging
logging.basicConfig(format='%(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


# Init bot
tg_bot = Bot(settings.TELEGRAM['token'])


def getListOfFiles(dirName):
    """
    create a list of file and sub directories
    names in the given directory
    """
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)

    return allFiles


def sha256_checksum(filename, block_size=65536):
    """
    return SHA-256 checksum of file
    """
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


def jsonToRGB(string):
    """
    decode color in JSON format stored in DB
    """
    color = tuple(json.loads(string))
    color1_rgb = sRGBColor(*color, is_upscaled=True)
    return convert_color(color1_rgb, LabColor)


def _index_images_thread(file):
    """
    single thread of image indexing
    """
    db.Picture.addToIndex(filename=file)


def index_images():
    """
    initiate image indexation
    """
    file_list = getListOfFiles(settings.IMAGES_PATH)

    with mp.Pool() as p:
        p.map(_index_images_thread, file_list)

    # db.session.commit()

    tg_bot.send_message(
        settings.TELEGRAM['sudo_users'][0],
        'Indexing finished successfully')


def post_to_telegram(what=False):
    """
    create post on channel

    what: type of post. can be 'single' or 'compilation'
    """

    # decide if it will be a single image or compilation
    choice = secrets.randbelow(100)

    if choice <= 30 or what == 'compilation':  # post compilation
        similar_images = db.Picture.getColorCompitation(
            settings.COMPILATION_NUM)

        media_to_send = [
            InputMediaPhoto(open(image.filename, 'rb'))
            for image in similar_images
        ]

        msgs = tg_bot.send_media_group(
            settings.TELEGRAM['channel_id'],
            media_to_send)

        for image in similar_images:
            image.markAsPosted(msgs[0].media_group_id)

    elif choice > 30 or what == 'single':  # post single image
        image = db.Picture.getRandomImage()
        post = tg_bot.send_photo(
            chat_id=settings.TELEGRAM['channel_id'],
            photo=open(image.filename, 'rb'))
        # Attach like button
        update_like_button(settings.TELEGRAM['channel_id'], post.message_id)
        # Mark image as posted
        image.markAsPosted(post.message_id)


def update_like_button(chat_id, post_id):
    keyboard = [[InlineKeyboardButton(
        f"🤍 {(db.Likes.getCount(post_id) or '')}",
        callback_data=f'like-{post_id}')]]
    tg_bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=post_id,
        reply_markup=InlineKeyboardMarkup(keyboard))


def restricted(func):
    """
    restrict access to commands
    """
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in settings.TELEGRAM['sudo_users']:
            logger.warning(f"Unauthorized access denied for {user_id}.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped


def getDBstats():
    """
    get stats from database
    """

    count_today = db.Picture.where(ts_posted__day_le=1).count()

    count_total = (
        db.session.query(db.func.count(db.Picture.id).label('count'))
        .first().count)

    last_post = (
        db.session.query(db.Picture.ts_posted)
        .filter(db.Picture.ts_posted.isnot(None))
        .order_by(db.Picture.ts_posted.desc()).limit(1).first()).ts_posted

    return {
        'today': count_today,
        'total': count_total,
        'last_post': last_post,
    }
