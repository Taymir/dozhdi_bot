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
    await message.reply("Добро пожаловать! \n"
                        f"Отправьте своё местоположение, чтобы получить карту осадков")


@dp.message_handler(commands='test')
async def test_command(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup([[
        types.reply_keyboard.KeyboardButton(text="Отправить геопозицию", request_location=True),
    ]])
    await message.reply("Скиньте геопозицию", reply_markup=markup)


@dp.message_handler(commands='test2')
async def test2_command(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardRemove()
    await message.reply("Кнопка убрана", reply_markup=markup)


@dp.message_handler(commands='test3')
async def test3_command(message: types.Message):
    save_flag = False
    #coords = (55.8974, 37.538481)  #MSK
    coords = (59.911052, 30.392958)  #SPB
    #coords = (48.708177, 44.526469)  #Волгоград
    lat, lon = coords

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
    # Если найден с другим статусом, то вернуть его
    if found_request:
        if found_request['status'] == 'recieved':
            file = found_request['mp4_file']
            url = dozhdi_parser.make_url(*coords)
            msg = await message.reply_animation(file, caption=f"<a href='{url}'>Посмотреть в браузере</a>",
                                                parse_mode='HTML')
            return #TODO: Refactor: extract same code to one method
        else:
            # Если найден со статусом processing, to wait
            reply = "<i>Ждем догрузки информации по координатам: {}, {}...</i>".format(*coords)
            tmp_msg = await message.reply(reply, reply_markup=types.ReplyKeyboardRemove(), parse_mode='HTML')

            await asyncio.sleep(15)
            found_request = db.requests.find_one({'_id': found_request['_id']})
            if found_request['status'] == 'recieved':
                file = found_request['mp4_file']
                url = dozhdi_parser.make_url(*coords)
                msg = await message.reply_animation(file, caption=f"<a href='{url}'>Посмотреть в браузере</a>",
                                                    parse_mode='HTML')
                return

    # Иначе инициировать новый запрос со статусом processing
    start = time.time()
    inserted_doc = db.requests.insert_one({
        'user_id': message.from_user.id,
        'location': {'type': 'Point', 'coordinates': [lon, lat]},
        'mp4_file': None,
        'status': 'processing',
        'datetime': datetime.datetime.now()
    })

    reply = "<i>Проверяем осадки по координатам: {}, {}...</i>".format(*coords)
    tmp_msg = await message.reply(reply, reply_markup=types.ReplyKeyboardRemove(), parse_mode='HTML')

    mp4_file = await dozhdi_parser.request_mp4(*coords)
    url = dozhdi_parser.make_url(*coords)

    file = types.input_file.InputFile(mp4_file, filename="weather.mp4")

    msg = await message.reply_animation(file, caption=f"<a href='{url}'>Посмотреть в браузере</a>", parse_mode='HTML')
    if not save_flag:
        await dozhdi_parser.remove_file(mp4_file)

    # Здесь поменять статус на recieved
    db.requests.update_one({'_id': inserted_doc.inserted_id}, {
        '$set': {
            'mp4_file': msg.animation.file_id,
            'status': 'recieved',
        }
    })

    await tmp_msg.delete()
    end = time.time()
    print(f"Время выполнения: {end-start}")


@dp.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    save_flag = True
    lat = message.location.latitude
    lon = message.location.longitude

    reply = "Проверяем осадки по координатам: latitude:  {}\nlongitude: {}".format(lat, lon)
    tmp_msg = await message.answer(reply, reply_markup=types.ReplyKeyboardRemove())

    mp4_file = await dozhdi_parser.request_mp4(lat, lon)
    file = types.input_file.InputFile(mp4_file, filename="weather.mp4")
    if not save_flag:
        await dozhdi_parser.remove_file(mp4_file)

    await message.reply_animation(file)
    await tmp_msg.delete()


def main():
    try:
        executor.start_polling(dp, skip_updates=True)
    except KeyboardInterrupt:
        print("Received exit, exiting")



if __name__ == '__main__':
    main()
