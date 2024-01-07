import os
import telebot
from telebot import types

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

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
        btn1 = types.KeyboardButton('Кнопка 1')
        btn2 = types.KeyboardButton('Кнопка 2')
        btn3 = types.KeyboardButton('Кнопка 3')
        markup.add(btn1,btn2,btn3)
        bot.send_message(message.from_user.id,'Укажите 2 валюты для конвертации',reply_markup=markup)
    pass

def run_bot():
    bot.polling(non_stop=True, interval=0)

if __name__ == '__main__':
    run_bot()