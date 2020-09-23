FROM python:3.8-slim-buster

LABEL maintainer="me@iriscot.org"

COPY . .

RUN pip3 install -r requirements.txt

VOLUME /usr/share/autoposter_images

CMD ["python","app.py"]
