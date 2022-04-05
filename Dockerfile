FROM python:3-alpine

LABEL com.telegram-moviebot.version="0.1"

WORKDIR /

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create unprivileged user to run the script
RUN addgroup -S telegram && adduser -S telegram -G telegram
USER telegram:telegram

COPY . .

CMD [ "python", "/telegram-moviebot/telegram-moviebot.py" ]