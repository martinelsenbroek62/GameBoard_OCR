FROM python:3.7

WORKDIR /
COPY . /

RUN apt-get install libglib2.0-0

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

RUN ["chmod", "+x", "/ffmpeg"]
RUN ["chmod", "+x", "/startService.sh"]
ENTRYPOINT ./startService.sh