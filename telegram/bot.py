import logging
import sys
sys.path.append('.')
import aiohttp
import asyncio
import settings
import re
from settings import BACKEND_HOST, TELEGRAM_BOT_TOKEN
from abc import ABC,abstractmethod
from urllib.parse import urlunparse
import urllib3
from collections import namedtuple
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from typing import NamedTuple


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


commands = []
menu_keyboard = [['Конвертировать'],['узнать курс валют'],['Список команд'],['Управление']]


class UrlComponents(NamedTuple):
    scheme: str = 'http'
    netloc: str = f'{BACKEND_HOST}:5000'
    url: str = '/'
    path: str = ''
    query: dict = ''
    fragment: str = ''

class BotCore:
    global commands

    def __init__(self,token) -> None:
        self.application = ApplicationBuilder().token(token).build()
        [self.application.add_handler(c) for c in commands]

    def run(self):
        self.application.run_polling()


class RegisterCommand:

    def __init__(self,handler,command: str = None) -> None:
        self.command = command
        self.handler = handler

    def __call__(self,obj,*args,**kwargs):
        if self.command is None:
            self.command = obj.filter
        commands.append(self.handler(self.command,obj.execute))
        return obj(*args,**kwargs)


class Command(ABC):
    @staticmethod
    @abstractmethod
    async def execute(update: Update, context: ContextTypes): pass


@RegisterCommand(CommandHandler,'start')
class Start(Command):
    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_markup = ReplyKeyboardMarkup([], resize_keyboard=True)
        message = 'что бы узнать все команды отправьте в чат /help,\
                или выберите опцию на клавиатуре:'
        message = ' '.join(message.split())
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=reply_markup)    



@RegisterCommand(CommandHandler,'help')
class CommandList(Command):
    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        '''/help - Выводит справочную информацию о командах бота'''
        _commands = [c for c in commands if isinstance(c,CommandHandler)]
        descriptions = [' '.join(d.callback.__doc__.split()) for d in _commands if d.callback.__doc__]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='\n\n'.join(descriptions))


@RegisterCommand(CommandHandler,'list_currencies')
class ListCurrencies(Command):
    url = urlunparse(UrlComponents(url='/info'))

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        '''/list_currencies - выводи список доступных валют'''
        url = ListCurrencies.url
        async with aiohttp.ClientSession() as session:
            response = await session.get(url)
            data = await response.json()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=' '.join(data['currencies']))


@RegisterCommand(CommandHandler,'last_course')
class LastCourse(Command):
    url: str = urlunparse(UrlComponents(url='/last_currency_rate/{}/{}'))

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        '''/last_course <base_currency> <quoted_currency> - получить текущий курс мосбиржи\
            базовой валюты(base_currency) в котируемой валюте(quoted_currency)'''
        try:
            firs_currency = context.args[0]
            second_currency = context.args[1]
            url = LastCourse.url.format(firs_currency,second_currency)
            async with aiohttp.ClientSession() as session:
                response = await session.get(url)
                if response.status != 200:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text='''Ошибка: Не получилось конвертировать валюты,\
                        проверьте вводные данные,\
                        возможно требуемые валюты отсутствуют.''')
                    return
                data = await response.json()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=str(data))
        except IndexError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Отсутствует требуемое значение')
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=str(e))


@RegisterCommand(CommandHandler,'convert')
class Convert(Command):
    url: str = urlunparse(UrlComponents(url='/convert/{}/{}/{}'))

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        '''/convert <value> <base_currency> <quoted_currency> - конвертирует\
        числовое значение(value) базовой валюты(base_currency) в\
        котируемую валюту(quoted_currency) по последнему курсу мосбиржи'''
        try:
            value = float(context.args[0])
            firs_currency = context.args[1]
            second_currency = context.args[2]
            url = Convert.url.format(value,firs_currency,second_currency)
            async with aiohttp.ClientSession() as session:
                response = await session.get(url)
                if response.status != 200:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text='''Ошибка: Не получилось конвертировать валюты,
                        проверьте вводные данные,
                        возможно требуемые валюты отсутствуют.''')
                    return
                data = await response.json()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=str(data))
        except IndexError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Отсутствует требуемое значение')
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=str(e))


@RegisterCommand(MessageHandler)
class ActionCommandManager(Command):
    keybord = [['Конвертировать'],['Узнать курс валют'],['Получить исторический курс'],['Список команд']]
    filter = (filters.Text([w[0] for w in keybord]))
    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text.lower()
        match message_text:
            case 'узнать курс валют':
                pass
            case'конвертировать':
                pass
            case 'Получить исторический курс':
                pass
            case 'cписок команд':
                pass
            case _:
                pass


@RegisterCommand(MessageHandler)
class CurrenciesCommandManager(Command):
    keybord = urllib3.request('GET',urlunparse(UrlComponents(url='/info'))).json()['currencies']
    filter = (filters.Text([w[0] for w in keybord]))
    @staticmethod
    async def execute(update: Update, context: ContextTypes):
        pass


if __name__ == '__main__':
    BotCore(TELEGRAM_BOT_TOKEN).run()




    
