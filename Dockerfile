FROM python:3.7-slim-buster
WORKDIR /app

COPY requirements.txt .
COPY ace-attorney-reddit-bot/requirements.txt ./requirements2.txt
RUN apt-get update && \
  apt-get install ffmpeg libsm6 libxext6 build-essential icu-devtools libicu-dev git -y && \
  pip install -r requirements2.txt && \
  pip install -r requirements.txt && \
  python -m spacy download en_core_web_sm && \
  apt-get clean && \
  rm -rf ~/.cache/pip/*

COPY . .

CMD python ./main.py
