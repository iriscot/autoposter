import os

TELEGRAM = {
    "token": os.environ.get('TG_TOKEN'),
    "channel_id": os.environ.get('CHANNEL_ID'),
    "sudo_users": [int(x) for x in os.environ.get('SUDO_USERS').split(';')]
}

POSTING_RATE_MIN = int(os.environ.get('POSTING_RATE_MIN'))
POSTING_RATE_MAX = int(os.environ.get('POSTING_RATE_MAX'))

DB = os.environ.get('DATABASE_CONN')

IMAGES_PATH = "/usr/share/autoposter_images/"

COMPILATION_NUM = int(os.environ.get('COMPILATION_NUM'))
