import datetime
import logging
import time

import aiogram.types.reply_keyboard

import settings
from aiogram import Bot, Dispatcher, executor, types
import pymongo, pymongo.errors
import dozhdi_parser
import asyncio

logging.basicConfig(level=logging.INFO)
bot = Bot(token=settings.token)
dp = Dispatcher(bot)

client = pymongo.MongoClient(host=settings.mongodb['host'], port=settings.mongodb['port'],
                             username=settings.mongodb['username'], password=settings.mongodb['password'],
                             tls=settings.mongodb['tls'])
db = client.dozhdi_bot


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    found_user = db.users.find_one({'user_id': message.from_user.id})
    if not found_user:
        db.users.insert_one({'user_id': message.from_user.id,
                             'first_name': message.from_user.first_name,
                             'username': message.from_user.username,
                             'language_code': message.from_user.language_code,
                             'location': None
                             })

    await help_command(message)


@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup([
        [
            types.reply_keyboard.KeyboardButton(text="Москва"),
            types.reply_keyboard.KeyboardButton(text="Санкт-Петербург")
         ],
        [types.reply_keyboard.KeyboardButton(text="Отправить геопозицию", request_location=True)]
    ])

    await message.reply("Добро пожаловать! \n"
                        f"Отправьте своё местоположение, чтобы получить карту осадков", reply_markup=markup)


@dp.message_handler(commands='test3')
async def test3_command(message: types.Message):
    #coords = (55.8974, 37.538481)  #MSK
    coords = (59.911052, 30.392958)  #SPB
    #coords = (48.708177, 44.526469)  #Волгоград

    await weather_request(coords, message)


@dp.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    save_flag = True
    lat = message.location.latitude
    lon = message.location.longitude
    coords = (lat, lon)

    db.users.update_one({
        'user_id': message.from_user.id
    }, {
        '$set': {
            'location': list(coords)[::-1]
        }
    })
    await weather_request(coords, message)


@dp.message_handler()
async def general_message(message: types.Message):
    city = message.text
    found = db.cities.find_one({'city': city})
    if not found:
        return await message.reply(f"Город {city} не найден. Попробуйте скинуть геолокацию")

    coords = found['location'][::-1]  # В БД координаты хранятся в обратном порядке: [lon, lat]
    await weather_request(coords, message)


async def weather_request(coords, message):
    # Поиск схожего запроса
    found_request = db.requests.find_one({
        'location': {
            '$near': {
                '$geometry': {
                    'type': 'Point',
                    'coordinates': list(coords)[::-1]
                },
                '$maxDistance': 10000
            }
        },
        'datetime': {
            '$gte': datetime.datetime.now() - datetime.timedelta(minutes=15)
        }
    }, sort=[('datetime', pymongo.DESCENDING)])

    if not settings.cache_requests:
        found_request = None

    # Если найден, то вернуть его
    if found_request:
        if found_request['status'] == 'recieved':
            return await reply_weather_animation(coords, found_request['mp4_file'], message)
        else:
            # Если найден со статусом processing, to wait
            reply = "<i>Получаем данные об осадках. Минутку...</i>"
            logging.debug("Waiting for db cache")
            tmp_msg = await message.reply(reply, parse_mode='HTML')

            await asyncio.sleep(20)
            # Повторно проверяем, обновился ли статус
            found_request = db.requests.find_one({'_id': found_request['_id']})
            if found_request['status'] == 'recieved':
                return await reply_weather_animation(coords, found_request['mp4_file'], message)
            await tmp_msg.delete()

    # Иначе инициировать новый запрос со статусом processing
    start = time.time()
    inserted_doc = db.requests.insert_one({
        'user_id': message.from_user.id,
        'location': {'type': 'Point', 'coordinates': list(coords)[::-1]},
        'mp4_file': None,
        'status': 'processing',
        'datetime': datetime.datetime.now()
    })

    reply = "<i>Получаем данные об осадках. Минутку...</i>"
    tmp_msg = await message.reply(reply, parse_mode='HTML')
    mp4_file = await dozhdi_parser.request_mp4(*coords)
    file = types.input_file.InputFile(mp4_file, filename="weather.mp4")
    msg = await reply_weather_animation(coords, file, message)
    if not settings.save_flag:
        await dozhdi_parser.remove_file(mp4_file)

    # поменять статус на recieved
    db.requests.update_one({'_id': inserted_doc.inserted_id}, {
        '$set': {
            'mp4_file': msg.animation.file_id,
            'status': 'recieved',
        }
    })

    await tmp_msg.delete()
    end = time.time()
    logging.debug(f"Время выполнения: {end - start}")


async def reply_weather_animation(coords, file, message):
    url = dozhdi_parser.make_url(*coords)
    return await message.reply_animation(file, caption=f"<a href='{url}'>Посмотреть в браузере</a>",
                                         parse_mode='HTML')


def main():
    try:
        executor.start_polling(dp, skip_updates=True)
    except KeyboardInterrupt:
        print("Received exit, exiting")


if __name__ == '__main__':
    main()
