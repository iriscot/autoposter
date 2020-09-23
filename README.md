# autoposter
Telegram bot that posting random photos and compilations to your channel 🖼.

A working example can be found at @scievo channel, subscribe pls ^^

# What it does
1. Automatic posting photos at random intervals;
2. Colour-based compilations of photos;
3. ❤️ buttons with a counter for posts;
4.  Management via telegram bot;
5.  Channel insights;
6.  Add new pictures on the fly by sending them to the bot.

# Usage

Get the docker image:
```
docker pull iriscot/autoposter
```

Run the container with environment vars matching your config, an example env-file provided:
```
docker run --env-file env.file iriscot/autoposter
```

Alternatively, you can simply export env-variables and run `app.py` in python.

# Configuration

Settings are made using environment variables. You can find sample config in `env.file`.

**Telegram settings**
* **TG_TOKEN** - A bot token. Obtain one from @botfather. This bot must have admin rights in your channel;
* **CHANNEL_ID** - ID or @username of your channel. You must use ID if your channel is private;
* **SUDO_USERS** - List of bot administrators, separated with a semicolon. The first user in the list receives system announcements.

**Posting**
Bot posts at random times between those intervals: 
* **POSTING_RATE_MIN** - Minimum posting interval, in minutes;
* **POSTING_RATE_MAX** - Maximum posting interval, in minutes;
* **COMPILATION_NUM** - Maximum number of photos in colour-compilation.

**System**
* **DATABASE_CONN** - Database connection string. See: https://docs.sqlalchemy.org/en/13/core/engines.html
If you are a using file-backed SQLite database, you have to set `check_same_thread` to `false`.
