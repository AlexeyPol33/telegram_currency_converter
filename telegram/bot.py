import logging
import sys
sys.path.append('.')
import os
import telebot
import requests
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

        currencies, = list(await asyncio.gather(get_currencies()))
        reply_markup = ReplyKeyboardMarkup(currencies, resize_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите целивую валюту:',reply_markup=reply_markup)
    elif message_text == 'cписок команд':
        pass
    elif message_text == 'yправление':
        pass


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE): #TODO
    сurrency_pair = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=сurrency_pair)

async def exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    pass 

def run_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler('start',start)
    caps_handler = CommandHandler('caps',caps)
    exchange_rate = CommandHandler('exchange_rate',exchange_rate)
    convert_handler = CommandHandler('convert',convert)
    menu_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), menu)

    application.add_handler(start_handler)
    application.add_handler(caps_handler)
    application.add_handler(convert_handler)
    application.add_handler(menu_handler)
    application.add_handler(exchange_rate)

    application.run_polling()

if __name__ == '__main__':
    run_bot()
