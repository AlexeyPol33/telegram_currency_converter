import logging
import sys
sys.path.append('.')
import os
import re
import aiohttp
import asyncio
import settings
from settings import BACKEND_HOST, TELEGRAM_BOT_TOKEN

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

menu_keyboard = [['Конвертировать'],['узнать курс валют'],['Список команд'],['Управление']]

async def get_currencies():
    async with aiohttp.ClientSession() as session:
        response = await session.get(f'http://{BACKEND_HOST}:5000/info')
        data = await response.json()
        return data['currencies']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Я бот')    
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    await context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите опцию:', reply_markup=reply_markup)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.lower()
    print(message_text)
    if message_text == 'меню':

        reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите опцию:', reply_markup=reply_markup)
    elif message_text == 'узнать курс валют':

        currencies = list(await asyncio.gather(get_currencies()))
        reply_markup = ReplyKeyboardMarkup(currencies, resize_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите целивую валюту:',reply_markup=reply_markup)
    elif message_text == 'cписок команд':
        commands = [
            '/currency_rate базовая валюта/котируемая валюта - Показывает курс базовый валюты в котируемой',
            ''
            ]
        pass
    elif message_text == 'yправление':
        pass

async def currency_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    currency_pair = ''.join(context.args).upper()
    if len (currency_pair) == 7:
        currency_pair = re.match(r'(\w\w\w)/(\w\w\w)',currency_pair).groups()
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Не верный формат валютной пары')
        return

    async with aiohttp.ClientSession() as session:
        response = await session.get(f'http://{BACKEND_HOST}:5000/last_currency_rate/{currency_pair[0]}/{currency_pair[1]}')
        if response.status != 200:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Ошибка: Не получилось\
                                      конвертировать валюты, проверьте вводные данные, возможно требуемые валюты отсутствуют.')
            return

        data = await response.json()

    datetime = data['datetime']
    currency_name = data['currency_name']
    price = data['price']
    message = f'{datetime}    {currency_name}    {price}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 2 or context.args[1] != 7:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Не верный формат ввода')
        return

    value = context.args[0]
    currency_pair = re(r'(\w\w\w)/(\w\w\w)',context.args[1]).groups()
    async with aiohttp.ClientSession() as session:
        response = await session.get(f'/convert/{value}/{currency_pair[0]}/{currency_pair[1]}')
        if response.status != 200:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Ошибка: Не получилось\
                                      конвертировать валюты, проверьте вводные данные, возможно требуемые валюты отсутствуют.')
            return
        
        data = await response.json()

    datetime = data['datetime']
    currenvy_name = data['currency_name']
    price = data['price']
    message = f'{datetime}      {currenvy_name}     {price}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


def run_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler('start',start)
    currency_rate_handler = CommandHandler('currency_rate',currency_rate)
    convert_handler = CommandHandler('convert',convert)
    menu_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), menu)

    application.add_handler(start_handler)
    application.add_handler(convert_handler)
    application.add_handler(menu_handler)
    application.add_handler(currency_rate_handler)

    application.run_polling()

if __name__ == '__main__':
    run_bot()
