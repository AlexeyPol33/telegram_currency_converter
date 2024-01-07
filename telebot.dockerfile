FROM python:3.10.11

WORKDIR /telegram_bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /telegram_bot/

CMD python telegram/bot.py run_bot
