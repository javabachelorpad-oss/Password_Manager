from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import json
from app import sql
import connect
import string
import random
from cryptography.fernet import Fernet
import hashlib
import base64


bot = Bot(token=connect.API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


password = b'Password7774541'                              # Пароль для шифрования
hashed_password = hashlib.sha256(password).digest() # Создаем хеш от пароля
key = base64.urlsafe_b64encode(hashed_password)     # Приводим хеш к нужному формату
cipher_suite = Fernet(key)                          # Создаем шифр с использованием ключа



def encrypt_dict_values(d): # Функция для рекурсивного шифрования значений словаря
    for key, value in d.items():
        if isinstance(value, dict):
            encrypt_dict_values(value)
        elif isinstance(value, str):
            d[key] = cipher_suite.encrypt(value.encode()).decode()

def decrypt_dict_values(d): # Функция для рекурсивного дешифрования значений словаря
    for key, value in d.items():
        if isinstance(value, dict):
            decrypt_dict_values(value)
        elif isinstance(value, str):
            d[key] = cipher_suite.decrypt(value.encode()).decode()


sql.create_table() # Создаем таблицу, если она отсутствует


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """  Записывает информацию о пользователе в базу данных, если пользователь новый.
    
    :param user_id: Id пользователя
    :param data_reg: Дата регистрации пользователя
    :param message: Объект сообщения.
    :return: Сообщение о приветствии нового пользователя или профиль существующего пользователя.
    :rtype: str
    """
    user_id = message.from_user.id
    user = sql.get_user(user_id)
    keyboard = InlineKeyboardMarkup()

    if not user:
        data_reg = datetime.datetime.now().strftime("%d.%m.%Y")
        sql.add_user(user_id, 'pos', data_reg)  # Добавляем пользователя
        sql.update_user_pos(user_id, 'start')   # Фиксация положения пользователя

        text = "<b>🔐 BotGenPass</b> \n\nДобро пожаловать дорогой друг! \nСгенерируй свой <b>первый пароль</b> кликнув на кнопку ниже. "
        keyboard.add(InlineKeyboardButton(
            text="🪄 Генератор пароля", callback_data="generate_password"))
        await message.reply(text, reply_markup=keyboard, parse_mode=types.ParseMode.HTML)
    else:
        text, keyboard = profile(user_id)
        await message.answer(text, reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


def profile(user_id):
    """ Возвращает информацию о профиле пользователя, включая последний сгенерированный пароль и его дату создания.

    :param user_id (int): Уникальный идентификатор пользователя.
    :param tuple: Кортеж, содержащий текст сообщения и клавиатуру для вывода профиля пользователя, если профиль существует, иначе None.
    """
    user = sql.get_user(user_id)
    if user:
        last_password_info = json.loads(user[4]) if user[4] else {}  # Загружаем информацию о последнем пароле из базы данных
        decrypt_dict_values(last_password_info)                      # Дешифруем значения

        text = (f"<b>🔐 BotGenPass</b>\n"
                f"\nДобро пожаловать в твой <b>защищённый менеджер паролей.</b>"
                f"\n\nПоследний пароль: <code>{last_password_info.get('pass', 'Нет данных')}</code>"
                f"\n<b>Дата генерации:</b> {last_password_info.get('date', 'Нет данных')}"
                )

        buttons = [
            types.InlineKeyboardButton(
                'Создать пароль', callback_data='generate_password'),
            types.InlineKeyboardButton(
                'Мои пароли', callback_data='my_password')
        ]
        keyboard_markup = types.InlineKeyboardMarkup(row_width=2)
        keyboard_markup.add(*buttons)
        return text, keyboard_markup
    else:
        return None


def my_password(user_id):
    """ Возвращает информацию о последнем пароле пользователя и его истории паролей.

    :param user_id (int): Уникальный идентификатор пользователя.
    :param tuple: Кортеж, содержащий текст сообщения и клавиатуру для вывода информации о паролях пользователя.
    """
    user = sql.get_user(user_id)
    if not user:
        return "Пользователь не найден в базе данных."

    # Извлекаем информацию о последнем пароле и истории паролей из базы данных
    last_password_info = json.loads(user[4])
    history_password = json.loads(user[5])

    # Дешифруем значения последнего и истории паролей
    decrypt_dict_values(last_password_info)
    for password_info in history_password:
        decrypt_dict_values(password_info)

    last_password_text = (f"<b>Последний пароль: ↩️</b>\n"
                          f"<b>Дата:</b> {last_password_info.get('date', 'Нет данных')}\n"
                          f"<b>Пароль:</b> <code>{last_password_info.get('pass', 'Нет данных')}</code>"
                          )
    
    history_password_text = "📑 История паролей:\n\n"
    for password_info in history_password:
        history_password_text += (f"Пароль: <code>{password_info.get('pass', 'Нет данных')}</code>\n"
                                  f"Дата создания: {password_info.get('date', 'Нет данных')}\n\n"
                                  )

    # Собираем текст сообщения
    text = last_password_text + "\n\n" + history_password_text

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🪄 Создать пароль", callback_data="generate_password"))
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="profile"))
    return text, keyboard


def generate_random_password(length=12):
    """ Генерирует случайный пароль заданной длины.

    :param length (int): Длина пароля. По умолчанию 12.
    :param str: Случайно сгенерированный пароль.
    """
    allowed_characters = string.ascii_letters + string.digits + "!@#$%^&*_"       # Набор допустимых символов для пароля
    password = ''.join(random.choice(allowed_characters) for _ in range(length))  # Генерация пароля случайной комбинацией символов
    return password


@dp.callback_query_handler()
async def inline_kb_answer_callback_handler(query: types.CallbackQuery):
    user_id = query.from_user.id

    if query.data == 'generate_password':       
        sql.update_user_pos(user_id, 'generate_password')                     # Фиксация положения пользователя
        generated_password = generate_random_password(random.randint(8, 14))  # Генерируем случайный пароль
        password_info = {"tag": "BotGenPas", "date": datetime.datetime.now().strftime("%d.%m.%Y"), "pass": generated_password}
       
        encrypt_dict_values(password_info)                              # Шифруем значения налету
        sql.update_last_password(user_id, json.dumps(password_info))    # Обновляем последний пароль пользователя
        sql.add_password_to_history(user_id, password_info)             # Добавляем сгенерированный пароль в историю паролей пользователя
        
        back_button = types.InlineKeyboardButton('⬅️ Назад', callback_data='profile')
        keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
        keyboard_markup.add(back_button)
        await query.message.edit_text(f"Сгенерированный пароль: <code>{generated_password}</code>", reply_markup=keyboard_markup, parse_mode="HTML")

    if query.data == 'profile':
        sql.update_user_pos(user_id, 'profile') # Фиксация положения пользователя
        text, keyboard = profile(user_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode=types.ParseMode.HTML)

    if query.data == 'my_password':
        sql.update_user_pos(user_id, 'my_password') # Фиксация положения пользователя
        text, keyboard = my_password(user_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode=types.ParseMode.HTML)



print("BotGenPas: Start polling")
if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    loop.run_forever()
