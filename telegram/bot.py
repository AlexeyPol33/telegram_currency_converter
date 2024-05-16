import logging
import sys
sys.path.append('.')
import aiohttp
import asyncio
import settings
import re
from settings import BACKEND_HOST, TELEGRAM_BOT_TOKEN,REDIS_HOST,REDIS_PORT
from abc import ABC,abstractmethod
from urllib.parse import urlunparse
import urllib3
from collections import namedtuple
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from typing import NamedTuple
import redis


commands = []
message_broker = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


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

    def __init__(self,handler, command: str = None) -> None:
        self.command = command
        self.handler = handler

    def __call__(self,obj):
        if self.command is None:
            self.command = obj.filter
        commands.append(self.handler(self.command,obj.execute))
        return obj


class Command(ABC):
    @staticmethod
    @abstractmethod
    async def execute(update: Update, context: ContextTypes): pass


@RegisterCommand(CommandHandler,'start')
class Start(Command):
    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_broker_name = f'{update.effective_chat.id}'
        reply_markup = ReplyKeyboardMarkup(ActionCommandManager.keybord, resize_keyboard=True)
        message_broker.delete(message_broker_name)
        await ActionCommandManager.input_call(update, context)




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
    url = urlunparse(UrlComponents(url='/currency_list'))

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
    url: str = urlunparse(UrlComponents(url='/convert/{}/{}'))

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
    url: str = urlunparse(UrlComponents(url='/convert/{}/{}',query={'value':'{}'}))

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        '''/convert <value> <base_currency> <quoted_currency> - конвертирует\
        числовое значение(value) базовой валюты(base_currency) в\
        котируемую валюту(quoted_currency) по последнему курсу мосбиржи'''
        try:
            value = float(context.args[0])
            firs_currency = context.args[1]
            second_currency = context.args[2]
            url = Convert.url.format(firs_currency,second_currency,value)
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


@RegisterCommand(CommandHandler,'historical_course')
class HistoricalCourse(Command):
    url: str = None

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        '''/historical_course <base_currency> <quoted_currency> <date_frome> <date_till>'''
        return


class CommandManager(ABC):

    @staticmethod
    @abstractmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    @classmethod
    @abstractmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass


class InputManager():

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_broker_name: str = f'{update.effective_chat.id}'
        if message_broker.hlen(message_broker_name) == 0:
            return
        message_broker_dict = message_broker.hgetall(message_broker_name)
        for item in message_broker_dict.items():
            if not item[1]:
                obj = item[0].decode('utf-8')
                await eval(f'{obj}.input_call(update, context)')
                return
        action = message_broker_dict.pop(b'ActionCommandManager').decode('utf-8')
        context.args = [s.decode('utf-8') for s in message_broker_dict.values()]
        await eval(f'{action}.execute(update, context)')
        message_broker.delete(message_broker_name)
        await Start.execute(update,context)

@RegisterCommand(MessageHandler)
class ActionCommandManager(CommandManager):
    keybord = [['Конвертировать'],['Узнать текущий курс'],['Получить исторический курс'],['Список команд']]
    filter = (filters.Text([w[0] for w in keybord]))

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text: str = update.message.text.lower()
        message_broker_name: str = f'{update.effective_chat.id}'
        if message_broker.hlen(message_broker_name) > 0:
            message_broker.delete(message_broker_name)
        match message_text:
            case 'узнать текущий курс':
                message_broker.hset(
                    name=message_broker_name,
                    mapping={
                        'ActionCommandManager':'LastCourse',
                        'FirsCurrencyCommandManager':'',
                        'SecondCurrencyCommandManager':'',
                    }
                )
            case'конвертировать':
                message_broker.hset(
                    name=message_broker_name,
                    mapping={
                        'ActionCommandManager':'Convert',
                        'ValueCommandManager':'',
                        'FirsCurrencyCommandManager':'',
                        'SecondCurrencyCommandManager':'',
                    }
                )
            case 'получить исторический курс':
                message_broker.hset(
                    name=message_broker_name,
                    mapping={
                        'ActionCommandManager':'HistoricalCourse',
                        'FirsCurrencyCommandManager':'',
                        'SecondCurrencyCommandManager':'',
                        'DateFromCommandManager':'',
                        'DateTillCommandManager':'',
                        'FormatCommandManager':'',
                    }
                )
            case 'cписок команд':
                await CommandList.execute(update, context)
                return
        await InputManager.execute(update, context)

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_markup = ReplyKeyboardMarkup(cls.keybord, resize_keyboard=True)
        message = 'что бы узнать все команды отправьте в чат /help,\
                или выберите опцию на клавиатуре:'
        message = ' '.join(message.split())
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=reply_markup)  


@RegisterCommand(MessageHandler)
class CurrencyCommandManager(CommandManager):
    currencies = urllib3.request('GET',urlunparse(UrlComponents(url='/currency_list'))).json()['currencies']
    filter = filters.Text(currencies)
    keybord = [[key] for key in currencies]
    

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_broker_name: str = f'{update.effective_chat.id}'
        if message_broker.hlen(message_broker_name) == 0:
            return
        if not message_broker.hget(message_broker_name,'FirsCurrencyCommandManager'):
            await FirsCurrencyCommandManager.execute(update, context)
        else:
            await SecondCurrencyCommandManager.execute(update, context)

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return


class FirsCurrencyCommandManager(CurrencyCommandManager):

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text: str = update.message.text.upper()
        message_broker_name: str = f'{update.effective_chat.id}'
        message_broker.hset(
            name=message_broker_name,
            key='FirsCurrencyCommandManager',
            value=message_text)
        await InputManager.execute(update, context)

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_markup = ReplyKeyboardMarkup(cls.keybord, resize_keyboard=True)
        message = 'Выберите базовую валюту'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=reply_markup)


class SecondCurrencyCommandManager(CurrencyCommandManager):

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text: str = update.message.text.upper()
        message_broker_name: str = f'{update.effective_chat.id}'
        message_broker.hset(
            name=message_broker_name,
            key='SecondCurrencyCommandManager',
            value=message_text)
        await InputManager.execute(update, context)

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_markup = ReplyKeyboardMarkup(cls.keybord, resize_keyboard=True)
        message = 'Выберите котируемую валюту'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=reply_markup)


@RegisterCommand(MessageHandler)
class ValueCommandManager(CommandManager):
    filter = filters.Regex(r'\d*')

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_broker_name: str = f'{update.effective_chat.id}'
        message_text: str = update.message.text.replace(',','.')
        if message_broker.hlen(message_broker_name) == 0:
            return
        if message_broker.hget(message_broker_name, 'ValueCommandManager') is not None:
            try:
                value = float(message_text)
                message_broker.hset(
                    name=message_broker_name,
                    key='ValueCommandManager',
                    value=value)
            except:
                return
        await InputManager.execute(update, context)

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = 'Клавиатура скрыта, отправьте числовое значение в чат для продолжения'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=ReplyKeyboardRemove())


class FormatCommandManager(CommandManager):

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return


class DateTimeCommandManager(CommandManager):
    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return


class DateFromCommandManager(DateTimeCommandManager):

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return


class DateTillCommandManager(DateFromCommandManager):

    @staticmethod
    async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return

    @classmethod
    async def input_call(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return


if __name__ == '__main__':
    BotCore(TELEGRAM_BOT_TOKEN).run()