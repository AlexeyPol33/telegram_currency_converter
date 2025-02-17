![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-%23DD0031.svg?&style=for-the-badge&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?style=for-the-badge)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-323232?style=for-the-badge&logo=sqlalchemy&logoColor=red)

# Currency Converter Bot 💰  
Простой Telegram-бот для конвертации валют в реальном времени.

## 🚀 Функциональность  
- Конвертация всех валют, торгуемых на Московской бирже.  
- Кросс-конвертация валют.  
- Получение курса валютной пары за определённый промежуток времени.  
- Поддержка форматов: CSV, JSON, TXT, PNG.  
- Удобная клавиатура для быстрого взаимодействия.  

## 🛠 Технологии  
- **Язык**: Python 3.10.11  
- **Библиотеки**: aiohttp, SQLAlchemy, python-telegram-bot  
- **База данных**: PostgreSQL, Redis  
- **Контейнеризация**: Docker  

## 🔧 Установка и запуск  
1. В файле `docker-compose.yml` замените комментарий `#Your bot token` на ваш токен бота.  
2. Выполните команду:  

   ```sh
   docker-compose up --build
