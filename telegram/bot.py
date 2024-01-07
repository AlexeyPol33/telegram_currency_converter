import sys
sys.path.append('.')
import os
import telebot
import requests
from telebot import types
import settings
from settings import BACKEND_HOST, TELEGRAM_BOT_TOKEN


bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('МЕНЮ')
    markup.add(btn1)
    bot.send_message(message.from_user.id, 'Привет!', reply_markup=markup)

@bot.message_handler(content_types=['text'])
def menu(message):
    if message.text == 'МЕНЮ':

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        currencies = requests.get(f'http://{BACKEND_HOST}:5000/info').json()['currencies']
        btns = []
        for currency in currencies:
            btns.append(types.KeyboardButton(currency))
        markup.add(*btns)
        bot.send_message(message.from_user.id,'Укажите 2 валюты для конвертации',reply_markup=markup)
    pass

def run_bot():
    bot.polling(non_stop=True, interval=0)

if __name__ == '__main__':
    run_bot()