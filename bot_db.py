#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import utils as util
import settings
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from colorthief import ColorThief
from colormath.color_diff import delta_e_cie2000
from sqlalchemy_mixins import AllFeaturesMixin


engine = create_engine(
    settings.DB)
engine.connect()

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class BaseModel(Base, AllFeaturesMixin):
    """Base to create tables with mixins"""
    __abstract__ = True
    pass


class SubscribersLog(BaseModel):
    """Stores subscribers number across time"""
    __tablename__ = 'subs_log'
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    channel_id = Column(String(255), nullable=False)

    @classmethod
    def checkpoint(cls, channel):
        cls.create(
            number=util.tg_bot.get_chat_members_count(channel),
            date=datetime.datetime.now(),
            channel_id=str(channel))
        session.commit()

    @classmethod
    def plot(cls, channel):

        data_db = (
            cls.smart_query(filters={
                'channel_id': channel,
                'date__day_le': 30},
                sort_attrs=['-id']).all())

        plot_y = []
        plot_x = []

        for entry in data_db:
            plot_y.append(entry.number)
            plot_x.append(entry.date.day)

        ax = plt.figure().gca()
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#DDDDDD')
        ax.spines['bottom'].set_color('#DDDDDD')
        ax.set_title(
            "Подписчики за прошедший месяц",
            pad=15, color='#333333', weight='bold')
        ax.set_xlabel("Дата", color='#333333')
        ax.set_ylabel("Подписчики", color='#333333')

        plt.plot(plot_x, plot_y, 'r')

        # save in png format
        plt.savefig('subs_plot.png', format='png')


class Picture(BaseModel):
    """Stores indexed pictures"""
    __tablename__ = 'pictures'
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(255), nullable=False)
    color = Column(String(255), nullable=False)
    ts_posted = Column(DateTime(), nullable=True)
    ts_indexed = Column(DateTime(), nullable=False)
    post_id = Column(BigInteger(), nullable=True)

    def markAsPosted(self, message_id=0):
        self.ts_posted = datetime.datetime.now()
        self.post_id = message_id
        session.commit()

    @classmethod
    def addToIndex(cls, **kwargs):
        image_hash = util.sha256_checksum(kwargs['filename'])
        picture = session.query(cls).filter_by(file_hash=image_hash)
        if(picture.scalar()):
            util.logger.debug(
                'Attempted to add existing image to index, skipping...')
            return False
        image = ColorThief(kwargs['filename'])
        dominant_color = image.get_color(quality=6)
        cls.create(
            filename=kwargs['filename'],
            file_hash=util.sha256_checksum(kwargs['filename']),
            color=json.dumps(dominant_color),
            ts_indexed=datetime.datetime.now())
        session.commit()

    @classmethod
    def getRandomImage(cls, **kwargs):
        image = (
            session.query(cls)
            .filter(
                cls.ts_posted.is_(None),
                cls.id != kwargs.get('exclude', 0))
            .order_by(func.random())
            .limit(1)
            .first())
        if image is None:
            util.tg_bot.send_message(
                settings.TELEGRAM['sudo_users'][0],
                'Картинки кончились(')
            raise Exception('No more pictures in pool')
            return False
        return image

    @classmethod
    def getColorCompitation(cls, count, second_time=False):

        # Get the random reference image
        ref_image = cls.getRandomImage()

        ref_color = util.jsonToRGB(ref_image.color)

        results = []
        pictures_all = cls.all()
        for test_image in pictures_all:
            test_color = util.jsonToRGB(test_image.color)
            delta_e = delta_e_cie2000(ref_color, test_color)

            if (delta_e < 14) and (delta_e != 0) and (test_image not in results):
                results.append(test_image)

        if(len(results) < 2 and second_time is False):
            return cls.getColorCompitation(count, True)
        else:
            return results


class Likes(BaseModel):
    """Stores likes"""
    __tablename__ = 'likes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    post_id = Column(BigInteger, nullable=False)
    media_id = Column(Integer, ForeignKey('pictures.id'))
    date = Column(DateTime, nullable=False)

    @classmethod
    def like(cls, **kwargs):
        like = cls.where(
            post_id=kwargs['post_id'],
            user_id=kwargs['user_id']).first()
        if like is not None:
            like.delete()
        else:
            # if wasn't liked, like it then
            cls.create(**kwargs, date=datetime.datetime.now())
            session.commit()

    @classmethod
    def getCount(cls, post_id):
        return cls.where(post_id=post_id).count()


Base.metadata.create_all(engine)

BaseModel.set_session(session)
