import logging

import aiogram.types.reply_keyboard

import settings
from aiogram import Bot, Dispatcher, executor, types
import pymongo, pymongo.errors
import dozhdi_parser

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
async def test2_command(message: types.Message):
    save_flag = True
    send_flag = True
    coords = (55.8974, 37.538481)  #MSK
    coords = (59.911052, 30.392958)  #SPB
    #coords = (48.708177, 44.526469)  #Волгоград

    gif = await dozhdi_parser.request_gif(*coords)

    if send_flag:
        file = types.input_file.InputFile(gif, filename="weather.gif")
        await message.reply_animation(file)
    elif save_flag:
        with open('var/anim.gif', 'wb') as out:
            out.write(gif.read())
        await message.answer('done')


@dp.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    reply = "Проверяем осадки по координатам: latitude:  {}\nlongitude: {}".format(lat, lon)
    await message.answer(reply, reply_markup=types.ReplyKeyboardRemove())
    gif = await dozhdi_parser.request_gif(lat, lon)
    file = types.input_file.InputFile(gif, filename="weather.gif")
    await message.reply_animation(file)


def main():
    try:
        executor.start_polling(dp, skip_updates=True)
    except KeyboardInterrupt:
        print("Received exit, exiting")


if __name__ == '__main__':
    main()
