FROM python:3

WORKDIR telegram-moviebot

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "telegram-moviebot/telegram-moviebot.py" ]