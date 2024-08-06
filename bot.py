import json
import chardet
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Константы для файлов
BLOCKED_USERS_FILE = 'blocked_users.json'
MUTED_USERS_FILE = 'muted_users.json'

def read_json_with_encoding(filename):
    with open(filename, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    with open(filename, 'r', encoding=encoding) as file:
        return json.load(file)

# Функция для загрузки конфигурации
def load_config(filename='config.json'):
    """Загрузить конфигурацию из файла"""
    try:
        return read_json_with_encoding(filename)
    except FileNotFoundError:
        return {}

# Загрузка конфигурации
config = load_config()

# Токен бота и ID администраторов
TOKEN = config.get('TOKEN')
ADMIN_CHAT_ID = config.get('ADMIN_CHAT_ID')
ADMIN_USER_IDS = config.get('ADMIN_USER_IDS', [])

# Таймауты
MESSAGE_TIMEOUT = config.get('MESSAGE_TIMEOUT', 5)
MUTE_DURATION = config.get('MUTE_DURATION', 3600)

# Функции для работы с заблокированными и замученными пользователями
def load_blocked_users():
    try:
        return read_json_with_encoding(BLOCKED_USERS_FILE)
    except FileNotFoundError:
        return []

def save_blocked_users(blocked_users):
    with open(BLOCKED_USERS_FILE, 'w', encoding='utf-8') as file:
        json.dump(blocked_users, file)

def load_muted_users():
    try:
        return read_json_with_encoding(MUTED_USERS_FILE)
    except FileNotFoundError:
        return {}

def save_muted_users(muted_users):
    with open(MUTED_USERS_FILE, 'w', encoding='utf-8') as file:
        json.dump(muted_users, file)

blocked_users = load_blocked_users()
muted_users = load_muted_users()

# Словарь для хранения времени последнего сообщения
user_last_message_time = {}

# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Привет! Я бот для обратной связи. Используйте /help для получения списка команд.')

# Команда /help
async def help_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in ADMIN_USER_IDS:
        help_text = (
            "Доступные команды для администраторов:\n"
            "/start - Приветственное сообщение\n"
            "/help - Список доступных команд\n"
            "/banlist - Список заблокированных пользователей\n"
            "/unban <user_id> - Разблокировка пользователя по ID\n"
        )
    else:
        help_text = (
            "Добро пожаловать! Я бот для обратной связи.\n"
            "Вы можете отправлять мне сообщения, и я передам их администраторам.\n"
            "Если у вас есть вопросы или проблемы, воспользуйтесь командой /help для получения информации о ботах."
        )

    await update.message.reply_text(help_text)

# Команда /banlist
async def banlist(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton(f"Разблокировать {user}", callback_data=f"unblock_{user}")] for user in blocked_users]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Список заблокированных пользователей:', reply_markup=reply_markup)

# Обработка сообщения от пользователя
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    current_time = datetime.now()

    # Проверка на мут
    if user_id in muted_users:
        mute_end_time = datetime.fromisoformat(muted_users[user_id])
        if current_time < mute_end_time:
            return  # Игнорировать сообщения, пока идет мут

        # Удаляем пользователя из мутов, если срок закончился
        del muted_users[user_id]
        save_muted_users(muted_users)

    # Проверка на таймаут спама
    last_message_time = user_last_message_time.get(user_id, datetime.min)
    if (current_time - last_message_time).total_seconds() < MESSAGE_TIMEOUT:
        # Если сообщения приходят слишком часто, добавляем мут
        if user_id not in muted_users:
            muted_users[user_id] = (current_time + timedelta(seconds=MUTE_DURATION)).isoformat()
            save_muted_users(muted_users)
        return  # Игнорируем сообщение

    # Обновляем время последнего сообщения
    user_last_message_time[user_id] = current_time

    if user_id in blocked_users:
        return

    # Пересылаем сообщение администраторам
    forwarded_message = await context.bot.forward_message(
        chat_id=ADMIN_CHAT_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

    # Создаем сообщение с информацией о пользователе и кнопкой блокировки
    user_info = (f"Отправитель: {update.message.from_user.full_name}\n"
                 f"Юзернейм: @{update.message.from_user.username if update.message.from_user.username else 'Не указан'}\n"
                 f"ID: {user_id}\n"
                 f"Сообщение: {update.message.text}")

    keyboard = [[InlineKeyboardButton("Заблокировать", callback_data=f"block_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=user_info,
        reply_markup=reply_markup
    )

# Обработка нажатия кнопок
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user_id = int(data.split('_')[1]) if '_' in data else None

    if user_id is not None:
        if data.startswith('block_'):
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
                await query.edit_message_text(text=f"Пользователь {user_id} заблокирован.")
        elif data.startswith('unblock_'):
            if user_id in blocked_users:
                blocked_users.remove(user_id)
                save_blocked_users(blocked_users)
                await query.edit_message_text(text=f"Пользователь {user_id} разблокирован.")
        await banlist(query.message, context)

# Обработка команды /unban
async def unban(update: Update, context: CallbackContext):
    if context.args:
        user_id = int(context.args[0])
        if user_id in blocked_users:
            blocked_users.remove(user_id)
            save_blocked_users(blocked_users)
            await update.message.reply_text(f"Пользователь {user_id} разблокирован.")
        else:
            await update.message.reply_text(f"Пользователь {user_id} не найден в списке заблокированных.")
    else:
        await update.message.reply_text("Укажите ID пользователя для разблокировки.")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('banlist', banlist))
    application.add_handler(CommandHandler('unban', unban))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
