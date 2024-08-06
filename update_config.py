import json
import chardet

def read_json_with_encoding(filename):
    with open(filename, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    with open(filename, 'r', encoding=encoding) as file:
        return json.load(file)

def update_config(filename='config.json'):
    """Обновить конфигурацию через интерактивный интерфейс"""
    try:
        config = read_json_with_encoding(filename)
    except FileNotFoundError:
        config = {}
    
    print("Введите новые значения (оставьте пустым для сохранения старого значения):")
    
    token = input(f"Токен бота (текущее: {config.get('TOKEN', 'Не задано')}): ")
    admin_chat_id = input(f"ID администраторов (текущее: {config.get('ADMIN_CHAT_ID', 'Не задано')}): ")
    admin_user_ids = input(f"ID пользователей-администраторов (текущее: {config.get('ADMIN_USER_IDS', 'Не задано')}): ")
    message_timeout = input(f"Таймаут сообщения(в секундах) (текущий: {config.get('MESSAGE_TIMEOUT', 'Не задано')}): ")
    mute_duration = input(f"Продолжительность мута(в секундах) (текущая: {config.get('MUTE_DURATION', 'Не задано')}): ")
    
    # Обновляем конфигурацию
    if token:
        config['TOKEN'] = token
    if admin_chat_id:
        config['ADMIN_CHAT_ID'] = admin_chat_id
    if admin_user_ids:
        config['ADMIN_USER_IDS'] = [int(id.strip()) for id in admin_user_ids.split(',')]
    if message_timeout:
        config['MESSAGE_TIMEOUT'] = int(message_timeout)
    if mute_duration:
        config['MUTE_DURATION'] = int(mute_duration)
    
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=4)
    
    print("Конфигурация обновлена!")

if __name__ == "__main__":
    update_config()
