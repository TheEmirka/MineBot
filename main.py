import telebot
from telebot import types
import random
import time
import json
import os
from datetime import datetime, timedelta

# Инициализация бота
TOKEN = "7488424424:AAH_ugd6N13IHFCYMLw9dOlimovJRB-KKUg"
bot = telebot.TeleBot(TOKEN)

# Файл для хранения данных пользователей
USER_DATA_FILE = "user_data.json"

# Структура данных пользователя по умолчанию
default_user_data = {
    "balance": 0,  # доллары
    "pickaxe_level": 1,  # уровень кирки (до 50)
    "mine_level": 1,     # уровень шахты (до 10)
    "current_mine": "землянная 1",  # текущая шахта
    "mines_unlocked": ["землянная 1"],  # разблокированные шахты
    "resources": {
        "земля": 0,
        "дерево": 0,
        "камень": 0,
        "уголь": 0  # Добавляем новый ресурс
    },
    "last_bonus_time": None,  # время последнего получения бонуса
    "tasks": {
        "active": [],   # активные задания
        "completed": 0  # количество выполненных заданий
    },
    "resources_mined": {  # счетчики добытых ресурсов для заданий
        "земля": 0,
        "дерево": 0,
        "камень": 0,
        "уголь": 0  # Добавляем новый ресурс
    }
}

# Стоимость шахт
mine_prices = {
    "землянная 2": 10,
    "землянная 3": 25,
    "деревянная 1": 50,
    "деревянная 2": 100,
    "деревянная 3": 200,
    "каменная 1": 350,
    "каменная 2": 500,
    "каменная 3": 750,
    "угольная 1": 1000,  # Добавляем цены угольных шахт
    "угольная 2": 1500,
    "угольная 3": 2500
}

# Цены ресурсов
resource_prices = {
    "земля": 1,
    "дерево": 3,
    "камень": 5,
    "уголь": 8  # Добавляем цену на уголь
}

# Таймаут добычи (в секундах)
mining_timeout = 30

# Временные метки последней добычи
last_mining_time = {}

# Добавим словарь для отслеживания текущего меню пользователя
user_current_menu = {}

# Добавим порядок шахт (от худшей к лучшей)
mines_order = [
    "землянная 1", "землянная 2", "землянная 3",
    "деревянная 1", "деревянная 2", "деревянная 3",
    "каменная 1", "каменная 2", "каменная 3",
    "угольная 1", "угольная 2", "угольная 3"  # Добавляем угольные шахты
]

# Конфигурация заданий
tasks_config = {
    "земля": {
        "amounts": [20, 30, 40, 50, 75],
        "rewards": [10, 20, 35, 35, 50]
    },
    "дерево": {
        "amounts": [10, 15, 20, 25, 30],
        "rewards": [20, 30, 35, 45, 50]
    },
    "камень": {
        "amounts": [15, 30, 45],
        "rewards": [50, 75, 100]
    },
    "уголь": {  # Добавляем задания для угля
        "amounts": [10, 15, 25, 30],
        "rewards": [75, 90, 120, 150]
    }
}

# Загрузка данных пользователей
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Сохранение данных пользователей
def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Получение данных конкретного пользователя
def get_user_data(user_id):
    user_id = str(user_id)
    users_data = load_user_data()
    
    if user_id not in users_data:
        users_data[user_id] = default_user_data.copy()
        save_user_data(users_data)
    else:
        # Добавляем поле mine_level для существующих пользователей
        if "mine_level" not in users_data[user_id]:
            users_data[user_id]["mine_level"] = 1
        
        # Добавляем поле tasks для существующих пользователей
        if "tasks" not in users_data[user_id]:
            users_data[user_id]["tasks"] = {
                "active": [],
                "completed": 0
            }
        
        # Добавляем счетчики добытых ресурсов для заданий
        if "resources_mined" not in users_data[user_id]:
            users_data[user_id]["resources_mined"] = {
                "земля": 0,
                "дерево": 0,
                "камень": 0,
                "уголь": 0  # Добавляем уголь
            }
        elif "уголь" not in users_data[user_id]["resources_mined"]:
            users_data[user_id]["resources_mined"]["уголь"] = 0
            
        # Добавляем поле "уголь" в ресурсы для существующих пользователей
        if "уголь" not in users_data[user_id]["resources"]:
            users_data[user_id]["resources"]["уголь"] = 0
            
        save_user_data(users_data)
    
    # Инициализируем задания, если их нет
    users_data[user_id] = initialize_tasks(users_data[user_id])
    save_user_data(users_data)
    
    return users_data[user_id]

# Обновление данных пользователя
def update_user_data(user_id, new_data):
    user_id = str(user_id)
    users_data = load_user_data()
    users_data[user_id] = new_data
    save_user_data(users_data)

# Главное меню (Шахта, Меню и Помощь)
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("⛏ Шахта")
    btn2 = types.KeyboardButton("📋 Меню")
    btn3 = types.KeyboardButton("❓ Помощь")
    markup.row(btn1, btn2)
    markup.row(btn3)
    return markup

# Меню шахт
def mines_menu(user_data):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⬅️ Назад"))
    
    # Земляные шахты
    markup.add(types.KeyboardButton("🟤 Земля"))
    row = []
    for i in range(1, 4):
        mine_name = f"землянная {i}"
        button_text = mine_name
        
        # Если шахта не разблокирована, показываем цену
        if mine_name not in user_data["mines_unlocked"]:
            button_text += f" ({mine_prices[mine_name]}💲)"
        
        row.append(types.KeyboardButton(button_text))
    markup.add(*row)
    
    # Деревянные шахты
    markup.add(types.KeyboardButton("🟢 Дерево"))
    row = []
    for i in range(1, 4):
        mine_name = f"деревянная {i}"
        button_text = mine_name
        
        # Если шахта не разблокирована, показываем цену
        if mine_name not in user_data["mines_unlocked"]:
            button_text += f" ({mine_prices[mine_name]}💲)"
        
        row.append(types.KeyboardButton(button_text))
    markup.add(*row)
    
    # Каменные шахты
    markup.add(types.KeyboardButton("⚪ Камень"))
    row = []
    for i in range(1, 4):
        mine_name = f"каменная {i}"
        button_text = mine_name
        
        # Если шахта не разблокирована, показываем цену
        if mine_name not in user_data["mines_unlocked"]:
            button_text += f" ({mine_prices[mine_name]}💲)"
        
        row.append(types.KeyboardButton(button_text))
    markup.add(*row)
    
    # Угольные шахты
    markup.add(types.KeyboardButton("⚫ Уголь"))
    row = []
    for i in range(1, 4):
        mine_name = f"угольная {i}"
        button_text = mine_name
        
        # Если шахта не разблокирована, показываем цену
        if mine_name not in user_data["mines_unlocked"]:
            button_text += f" ({mine_prices[mine_name]}💲)"
        
        row.append(types.KeyboardButton(button_text))
    markup.add(*row)
    
    return markup

# Меню "Меню"
def options_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🔨 Улучшить"), types.KeyboardButton("🎁 Бонус"))
    markup.row(types.KeyboardButton("👤 Профиль"), types.KeyboardButton("💰 Продать"))
    markup.row(types.KeyboardButton("📋 Задания"), types.KeyboardButton("⬅️ Назад"))
    return markup

# Меню заданий
def tasks_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("⬅️ Назад"))
    return markup

# Меню продажи ресурсов
def sell_menu(user_data):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Добавляем кнопки продажи только для тех ресурсов, которые есть у пользователя
    buttons = []
    if user_data["resources"]["земля"] > 0:
        buttons.append(types.KeyboardButton("Продать землю"))
    
    if user_data["resources"]["дерево"] > 0:
        buttons.append(types.KeyboardButton("Продать дерево"))
    
    if user_data["resources"]["камень"] > 0:
        buttons.append(types.KeyboardButton("Продать камень"))
    
    if user_data["resources"]["уголь"] > 0:
        buttons.append(types.KeyboardButton("Продать уголь"))
    
    # Добавляем кнопки по 2 в ряд
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i + 1])
        else:
            markup.row(buttons[i])
    
    # Если есть хоть какие-то ресурсы, добавляем кнопку "Продать всё"
    if any(user_data["resources"].values()):
        markup.row(types.KeyboardButton("Продать всё"))
    
    markup.row(types.KeyboardButton("⬅️ Назад"))
    return markup

# Функция для расчета бонуса добычи (теперь с учетом уровня шахты)
def calculate_mining_bonus(user_data):
    pickaxe_bonus = user_data["pickaxe_level"] - 1  # бонус от уровня кирки
    mine_bonus = (user_data["mine_level"] - 1)  # бонус от уровня шахты (+1 за каждый уровень)
    return pickaxe_bonus + mine_bonus

# Добыча ресурсов в зависимости от шахты
def mine_resources(mine_name, user_data):
    bonus = calculate_mining_bonus(user_data)  # Общий бонус добычи
    
    if "землянная 1" in mine_name:
        return {"земля": random.randint(1, 3) + bonus}
    elif "землянная 2" in mine_name:
        return {"земля": random.randint(3, 5) + bonus}
    elif "землянная 3" in mine_name:
        return {"земля": random.randint(5, 8) + bonus}
    elif "деревянная 1" in mine_name:
        return {
            "дерево": random.randint(1, 3) + bonus,
            "земля": random.randint(5, 10) + bonus
        }
    elif "деревянная 2" in mine_name:
        return {
            "дерево": random.randint(3, 5) + bonus,
            "земля": random.randint(8, 12) + bonus
        }
    elif "деревянная 3" in mine_name:
        return {
            "дерево": random.randint(5, 8) + bonus,
            "земля": random.randint(10, 15) + bonus
        }
    elif "каменная 1" in mine_name:
        return {
            "камень": random.randint(1, 3) + bonus,
            "дерево": random.randint(5, 10) + bonus
        }
    elif "каменная 2" in mine_name:
        return {
            "камень": random.randint(3, 5) + bonus,
            "дерево": random.randint(8, 12) + bonus
        }
    elif "каменная 3" in mine_name:
        return {
            "камень": random.randint(5, 8) + bonus,
            "дерево": random.randint(10, 15) + bonus
        }
    elif "угольная 1" in mine_name:
        return {
            "уголь": random.randint(1, 3) + bonus,
            "камень": random.randint(5, 10) + bonus
        }
    elif "угольная 2" in mine_name:
        return {
            "уголь": random.randint(3, 5) + bonus,
            "камень": random.randint(8, 12) + bonus
        }
    elif "угольная 3" in mine_name:
        return {
            "уголь": random.randint(5, 8) + bonus,
            "камень": random.randint(10, 15) + bonus
        }
    return {}

# Функция для определения лучшей шахты игрока
def get_best_mine(unlocked_mines):
    best_mine = "землянная 1"  # По умолчанию самая простая шахта
    best_index = 0
    
    for mine in unlocked_mines:
        if mine in mines_order:
            current_index = mines_order.index(mine)
            if current_index > best_index:
                best_index = current_index
                best_mine = mine
    
    return best_mine

# Меню выбора улучшения
def choose_upgrade_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("⛏ Улучшить кирку"))
    markup.row(types.KeyboardButton("🏭 Улучшить шахту"))
    markup.row(types.KeyboardButton("⬅️ Назад"))
    return markup

# Меню улучшения кирки
def upgrade_pickaxe_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("Улучшить кирку"))
    markup.row(types.KeyboardButton("⬅️ Назад"))
    return markup

# Меню улучшения шахты
def upgrade_mine_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("Улучшить шахту"))
    markup.row(types.KeyboardButton("⬅️ Назад"))
    return markup

# Инициализация заданий для нового пользователя
def initialize_tasks(user_data):
    if "tasks" not in user_data or not user_data["tasks"]["active"]:
        user_data["tasks"] = {
            "active": [],
            "completed": 0
        }
        user_data["resources_mined"] = {
            "земля": 0,
            "дерево": 0,
            "камень": 0,
            "уголь": 0  # Добавляем уголь
        }
        
        # Добавляем задание на землю (1 колонка)
        earth_task = generate_task_for_resource("земля")
        user_data["tasks"]["active"].append(earth_task)
        
        # Добавляем задание на дерево (2 колонка)
        wood_task = generate_task_for_resource("дерево")
        user_data["tasks"]["active"].append(wood_task)
        
        # Добавляем задание на камень (3 колонка)
        stone_task = generate_task_for_resource("камень")
        user_data["tasks"]["active"].append(stone_task)
        
        # Добавляем задание на уголь (4 колонка)
        coal_task = generate_task_for_resource("уголь")
        user_data["tasks"]["active"].append(coal_task)
    
    return user_data

# Генерация задания для конкретного типа ресурса с возможностью исключить определенные значения
def generate_task_for_resource(resource_type, exclude_amount=None):
    # Доступные уровни сложности
    available_amounts = tasks_config[resource_type]["amounts"].copy()
    
    # Если нужно исключить определенное значение и оно есть в списке
    if exclude_amount is not None and exclude_amount in available_amounts:
        available_amounts.remove(exclude_amount)
    
    # Если после исключения список пуст, вернем случайное значение из оригинального списка
    if not available_amounts:
        available_amounts = tasks_config[resource_type]["amounts"].copy()
    
    # Выбираем случайный уровень сложности из доступных
    amount_index = random.randint(0, len(available_amounts) - 1)
    amount = available_amounts[amount_index]
    
    # Находим индекс выбранного количества в оригинальном списке
    original_index = tasks_config[resource_type]["amounts"].index(amount)
    reward = tasks_config[resource_type]["rewards"][original_index]
    
    new_task = {
        "resource": resource_type,
        "amount": amount,
        "reward": reward,
        "progress": 0,
        "id": f"{resource_type}_{amount}_{int(time.time())}"  # уникальный ID
    }
    
    return new_task

# Добавим новую функцию для меню профиля
def profile_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("⬅️ Назад"))
    return markup

# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Приветственное сообщение с разметкой и версией игры
    welcome_text = (
        "*Добро пожаловать в игру MineGame!* 🎮 *v1.0.0*\n\n"
        "🌟 *Погрузись в увлекательный мир добычи ресурсов!* 🌟\n\n"
        "В этой игре ты станешь настоящим шахтёром:\n"
        "• ⛏ Добывай различные ресурсы: землю, дерево и камень\n"
        "• 💰 Продавай ресурсы и зарабатывай деньги\n"
        "• 🔨 Улучшай свою кирку до 50 уровня для увеличения эффективности\n"
        "• 🏗️ Открывай новые шахты с более ценными ресурсами\n"
        "• 🎁 Получай ежедневные бонусы\n\n"
        "*Начни своё увлекательное путешествие прямо сейчас!*\n"
    )
    
    # Создаем inline-кнопки для подписки на каналы
    markup = types.InlineKeyboardMarkup(row_width=1)
    sigma_button = types.InlineKeyboardButton("Подписаться на SigmaAI 🤖", url="https://t.me/SigmaAIchannel")
    ares_button = types.InlineKeyboardButton("Подписаться на AresAI 🚀", url="https://t.me/Aress_AI")
    markup.add(sigma_button, ares_button)
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)
    
    # Отправляем основное меню в отдельном сообщении
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=main_menu())

# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Обработка команды /help
    if message.text == "/help":
        help_command(message)
        return
    
    # Обработка кнопки "Назад" с учетом текущего меню
    elif message.text == "⬅️ Назад":
        current_menu = user_current_menu.get(user_id, "main")
        
        if current_menu == "profile":
            # Если пользователь в меню профиля, возвращаем его в меню опций
            user_current_menu[user_id] = "options"
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=options_menu())
        elif current_menu == "sell":
            # Если пользователь в меню продажи, возвращаем его в меню опций
            user_current_menu[user_id] = "options"
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=options_menu())
        elif current_menu == "tasks":
            # Если пользователь в меню заданий, возвращаем его в меню опций
            user_current_menu[user_id] = "options"
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=options_menu())
        elif current_menu == "upgrade_pickaxe" or current_menu == "upgrade_mine":
            # Если пользователь в меню улучшения кирки или шахты, возвращаем его в меню выбора улучшения
            user_current_menu[user_id] = "choose_upgrade"
            bot.send_message(message.chat.id, "Выберите, что хотите улучшить:", reply_markup=choose_upgrade_menu())
        elif current_menu == "choose_upgrade":
            # Если пользователь в меню выбора улучшений, возвращаем его в меню опций
            user_current_menu[user_id] = "options"
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=options_menu())
        elif current_menu in ["mines", "options"]:
            # Если пользователь в меню шахт или опций, возвращаем его в главное меню
            user_current_menu[user_id] = "main"
            bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu())
        else:
            # В любом другом случае возвращаем в главное меню
            user_current_menu[user_id] = "main"
            bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu())
    
    # Обработка кнопки "Шахта"
    elif message.text == "⛏ Шахта":
        user_current_menu[user_id] = "mines"
        bot.send_message(message.chat.id, "Выберите шахту:", reply_markup=mines_menu(user_data))
    
    # Обработка кнопки "Меню"
    elif message.text == "📋 Меню":
        user_current_menu[user_id] = "options"
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=options_menu())
    
    # Обработка кнопки "Помощь"
    elif message.text == "❓ Помощь":
        help_command(message)
    
    # Обработка кнопки "Улучшить"
    elif message.text == "🔨 Улучшить":
        user_current_menu[user_id] = "choose_upgrade"
        bot.send_message(message.chat.id, "Выберите, что хотите улучшить:", reply_markup=choose_upgrade_menu())
    
    # Обработка кнопки "Улучшить кирку"
    elif message.text == "⛏ Улучшить кирку":
        user_current_menu[user_id] = "upgrade_pickaxe"
        current_level = user_data["pickaxe_level"]
        
        # Проверяем, не достигнут ли максимальный уровень
        if current_level >= 50:
            bot.send_message(
                message.chat.id,
                "⛏ *Ваша кирка уже достигла максимального уровня!*\n"
                "Уровень кирки: *50/50*",
                parse_mode="Markdown"
            )
            # Возвращаем в меню выбора улучшения
            user_current_menu[user_id] = "choose_upgrade"
            bot.send_message(message.chat.id, "Что вы хотите улучшить?", reply_markup=choose_upgrade_menu())
            return
        
        next_level = current_level + 1
        upgrade_cost = 10 * current_level  # Линейная стоимость (+10 за каждый уровень)
        
        current_timeout = mining_timeout - (current_level - 1) * 0.3
        next_timeout = current_timeout - 0.3
        
        upgrade_text = (
            f"*⛏ Улучшение кирки:*\n\n"
            f"Текущий уровень: {current_level}/50\n"
            f"Следующий уровень: {next_level}/50\n\n"
            f"Текущий таймаут: {current_timeout:.1f} сек.\n"
            f"Следующий таймаут: {next_timeout:.1f} сек.\n\n"
            f"Стоимость улучшения: {upgrade_cost} $"
        )
        
        bot.send_message(message.chat.id, upgrade_text, parse_mode="Markdown", reply_markup=upgrade_pickaxe_menu())
    
    # Обработка кнопки "Улучшить шахту"
    elif message.text == "🏭 Улучшить шахту":
        user_current_menu[user_id] = "upgrade_mine"
        current_level = user_data["mine_level"]
        
        # Проверяем, не достигнут ли максимальный уровень
        if current_level >= 10:
            bot.send_message(
                message.chat.id,
                "🏭 *Ваша шахта уже достигла максимального уровня!*\n"
                "Уровень шахты: *10/10*",
                parse_mode="Markdown"
            )
            # Возвращаем в меню выбора улучшения
            user_current_menu[user_id] = "choose_upgrade"
            bot.send_message(message.chat.id, "Что вы хотите улучшить?", reply_markup=choose_upgrade_menu())
            return
            
        next_level = current_level + 1
        upgrade_cost = 10 * (2 ** (current_level - 1))  # Экспоненциальная стоимость (x2 за каждый уровень)
        
        current_bonus = (current_level - 1)  # +1 за каждый уровень
        next_bonus = current_bonus + 1
        
        upgrade_text = (
            f"*🏭 Улучшение шахты:*\n\n"
            f"Текущий уровень: {current_level}/10\n"
            f"Следующий уровень: {next_level}/10\n\n"
            f"Текущий бонус добычи: +{current_bonus}\n"
            f"Следующий бонус добычи: +{next_bonus}\n\n"
            f"Стоимость улучшения: {upgrade_cost} $"
        )
        
        bot.send_message(message.chat.id, upgrade_text, parse_mode="Markdown", reply_markup=upgrade_mine_menu())
    
    # Обработка кнопки "Улучшить кирку" из меню улучшения кирки
    elif message.text == "Улучшить кирку":
        current_level = user_data["pickaxe_level"]
        
        # Проверяем, не достигнут ли максимальный уровень
        if current_level >= 50:
            bot.send_message(
                message.chat.id,
                "⛏ *Ваша кирка уже достигла максимального уровня!*\n"
                "Уровень кирки: *50/50*",
                parse_mode="Markdown"
            )
            return
        
        upgrade_cost = 10 * current_level  # Линейная стоимость (+10 за каждый уровень)
        
        if user_data["balance"] >= upgrade_cost:
            user_data["balance"] -= upgrade_cost
            user_data["pickaxe_level"] += 1
            update_user_data(user_id, user_data)
            
            new_level = user_data["pickaxe_level"]
            new_timeout = mining_timeout - (new_level - 1) * 0.3
            
            upgrade_text = (
                f"*⛏ Кирка улучшена до уровня {new_level}/50!*\n\n"
                f"Новый таймаут: {new_timeout:.1f} сек."
            )
            
            bot.send_message(message.chat.id, upgrade_text, parse_mode="Markdown")
            
            # Если достигнут максимальный уровень, возвращаем в меню выбора
            if new_level >= 50:
                user_current_menu[user_id] = "choose_upgrade"
                bot.send_message(message.chat.id, "Выберите, что хотите улучшить:", reply_markup=choose_upgrade_menu())
        else:
            bot.send_message(
                message.chat.id,
                f"❌ *Недостаточно средств для улучшения!*\n"
                f"Требуется: *{upgrade_cost} $*\n"
                f"У вас: *{user_data['balance']} $*",
                parse_mode="Markdown"
            )
    
    # Обработка кнопки "Улучшить шахту" из меню улучшения шахты
    elif message.text == "Улучшить шахту":
        current_level = user_data["mine_level"]
        
        # Проверяем, не достигнут ли максимальный уровень
        if current_level >= 10:
            bot.send_message(
                message.chat.id,
                "🏭 *Ваша шахта уже достигла максимального уровня!*\n"
                "Уровень шахты: *10/10*",
                parse_mode="Markdown"
            )
            return
        
        upgrade_cost = 10 * (2 ** (current_level - 1))  # Экспоненциальная стоимость (x2 за каждый уровень)
        
        if user_data["balance"] >= upgrade_cost:
            user_data["balance"] -= upgrade_cost
            user_data["mine_level"] += 1
            update_user_data(user_id, user_data)
            
            new_level = user_data["mine_level"]
            new_bonus = (new_level - 1)
            
            upgrade_text = (
                f"*🏭 Шахта улучшена до уровня {new_level}/10!*\n\n"
                f"Новый бонус добычи: +{new_bonus}"
            )
            
            bot.send_message(message.chat.id, upgrade_text, parse_mode="Markdown")
            
            # Если достигнут максимальный уровень, возвращаем в меню выбора
            if new_level >= 10:
                user_current_menu[user_id] = "choose_upgrade"
                bot.send_message(message.chat.id, "Выберите, что хотите улучшить:", reply_markup=choose_upgrade_menu())
        else:
            bot.send_message(
                message.chat.id,
                f"❌ *Недостаточно средств для улучшения!*\n"
                f"Требуется: *{upgrade_cost} $*\n"
                f"У вас: *{user_data['balance']} $*",
                parse_mode="Markdown"
            )
    
    # Обработка кнопки "Бонус"
    elif message.text == "🎁 Бонус":
        current_time = datetime.now().timestamp()  # Сохраняем время как timestamp (число)
        
        # Проверяем, прошло ли 24 часа с последнего получения бонуса
        if user_data["last_bonus_time"] is None or current_time - user_data["last_bonus_time"] >= 24 * 60 * 60:
            bonus_amount = random.randint(3, 10)
            user_data["balance"] += bonus_amount
            user_data["last_bonus_time"] = current_time
            update_user_data(user_id, user_data)
            bot.send_message(message.chat.id, f"🎁 Вы получили бонус: *{bonus_amount} $*", parse_mode="Markdown")
        else:
            # Если не прошло 24 часа, вычисляем оставшееся время до следующего бонуса
            time_left = 24 * 60 * 60 - (current_time - user_data["last_bonus_time"])
            hours = int(time_left // 3600)
            minutes = int((time_left % 3600) // 60)
            
            bot.send_message(
                message.chat.id, 
                f"⏱ Вы сможете получить бонус через *{hours} ч. {minutes} мин.*",
                parse_mode="Markdown"
            )
    
    # Обработка кнопки "Продать"
    elif message.text == "💰 Продать":
        user_current_menu[user_id] = "sell"
        
        # Формируем текст с информацией о доступных ресурсах
        sell_text = "*💰 Ваши ресурсы для продажи:*\n\n"
        
        # Добавляем информацию о ресурсах с эмодзи
        for resource, amount in user_data["resources"].items():
            emoji = "🟤" if resource == "земля" else "🟢" if resource == "дерево" else "⚪" if resource == "камень" else "⚫"
            price = resource_prices[resource]
            total_price = amount * price
            sell_text += f"{emoji} {resource.capitalize()}: {amount} (цена: {price}$ за единицу, всего: {total_price}$)\n"
        
        sell_text += "\nВыберите ресурс для продажи:"
        
        bot.send_message(message.chat.id, sell_text, parse_mode="Markdown", reply_markup=sell_menu(user_data))
    
    # Обработка кнопки "Задания"
    elif message.text == "📋 Задания":
        user_current_menu[user_id] = "tasks"
        
        # Проверяем, есть ли активные задания
        if not user_data["tasks"]["active"] or len(user_data["tasks"]["active"]) < 3:
            # Если заданий нет или меньше 3, создаем новые задания
            user_data["tasks"]["active"] = []
            
            # Добавляем задание на землю (1 колонка)
            earth_task = generate_task_for_resource("земля")
            user_data["tasks"]["active"].append(earth_task)
            
            # Добавляем задание на дерево (2 колонка)
            wood_task = generate_task_for_resource("дерево")
            user_data["tasks"]["active"].append(wood_task)
            
            # Добавляем задание на камень (3 колонка)
            stone_task = generate_task_for_resource("камень")
            user_data["tasks"]["active"].append(stone_task)
            
            # Добавляем задание на уголь (4 колонка)
            coal_task = generate_task_for_resource("уголь")
            user_data["tasks"]["active"].append(coal_task)
            
            # Сбрасываем счетчики
            user_data["resources_mined"] = {
                "земля": 0,
                "дерево": 0,
                "камень": 0,
                "уголь": 0
            }
            
            update_user_data(user_id, user_data)
        
        tasks_text = "*📋 Ваши текущие задания:*\n\n"
        
        for i, task in enumerate(user_data["tasks"]["active"]):
            resource = task["resource"]
            amount = task["amount"]
            reward = task["reward"]
            progress = user_data["resources_mined"][resource]
            
            emoji = "🟤" if resource == "земля" else "🟢" if resource == "дерево" else "⚪" if resource == "камень" else "⚫"
            
            tasks_text += f"{i+1}. {emoji} Накопать *{amount}* {resource} (*{progress}/{amount}*)\n"
            tasks_text += f"   💰 Награда: *{reward} $*\n\n"
        
        bot.send_message(message.chat.id, tasks_text, parse_mode="Markdown", reply_markup=tasks_menu())
    
    # Обработка выбора шахты и проверка таймаута
    elif any(mine_type in message.text.lower() for mine_type in ["землянная", "деревянная", "каменная", "угольная"]):
        # Извлекаем название шахты без цены
        mine_name = message.text.split(" (")[0].lower()
        
        # Проверяем, открыта ли эта шахта
        if mine_name in user_data["mines_unlocked"]:
            # Проверяем таймаут добычи с учетом только кирки
            if user_id in last_mining_time:
                time_elapsed = time.time() - last_mining_time[user_id]
                current_timeout = mining_timeout - (user_data["pickaxe_level"] - 1) * 0.3  # Изменено с 0.1 на 0.3
                
                if time_elapsed < current_timeout:
                    time_left = current_timeout - time_elapsed
                    bot.send_message(
                        message.chat.id, 
                        f"⏱ Подождите *{time_left:.1f}* секунд перед следующей добычей",
                        parse_mode="Markdown"
                    )
                    return
            
            # Добываем ресурсы
            resources_mined = mine_resources(mine_name, user_data)
            
            # Обновляем данные пользователя
            for resource, amount in resources_mined.items():
                user_data["resources"][resource] += amount
                # Обновляем счетчики для заданий
                user_data["resources_mined"][resource] += amount
            
            user_data["current_mine"] = mine_name
            
            # Проверяем выполнение заданий
            tasks_completed = []
            tasks_to_remove = []
            
            for i, task in enumerate(user_data["tasks"]["active"]):
                resource_type = task["resource"]
                if user_data["resources_mined"][resource_type] >= task["amount"]:
                    # Задание выполнено
                    user_data["balance"] += task["reward"]
                    user_data["tasks"]["completed"] += 1
                    tasks_completed.append(task)
                    tasks_to_remove.append(i)
            
            # Удаляем выполненные задания и добавляем новые
            for i in sorted(tasks_to_remove, reverse=True):
                completed_task = user_data["tasks"]["active"][i]
                resource_type = completed_task["resource"]
                completed_amount = completed_task["amount"]  # Сохраняем количество из выполненного задания
                
                # Создаем новое задание того же типа, но с другим количеством
                new_task = generate_task_for_resource(resource_type, exclude_amount=completed_amount)
                
                # Заменяем старое задание новым
                user_data["tasks"]["active"][i] = new_task
                
                # Сбрасываем счетчик для этого типа ресурса
                user_data["resources_mined"][resource_type] = 0
            
            update_user_data(user_id, user_data)
            
            # Устанавливаем таймаут
            last_mining_time[user_id] = time.time()
            
            # Формируем сообщение о добыче
            mining_text = "⛏ *Вы добыли:*\n"
            for resource, amount in resources_mined.items():
                emoji = "🟤" if resource == "земля" else "🟢" if resource == "дерево" else "⚪" if resource == "камень" else "⚫"
                mining_text += f"{emoji} {resource.capitalize()}: {amount}\n"
            
            bot.send_message(message.chat.id, mining_text, parse_mode="Markdown")
            
            # Отправляем уведомления о выполненных заданиях
            for task in tasks_completed:
                resource = task["resource"]
                amount = task["amount"]
                reward = task["reward"]
                
                emoji = "🟤" if resource == "земля" else "🟢" if resource == "дерево" else "⚪" if resource == "камень" else "⚫"
                
                completion_text = (
                    f"✅ *Задание выполнено!*\n\n"
                    f"{emoji} Накопать {amount} {resource}\n"
                    f"💰 Награда: *{reward} $* (получена)"
                )
                
                bot.send_message(message.chat.id, completion_text, parse_mode="Markdown")
        
        else:
            # Шахта закрыта, предлагаем купить
            if mine_name in mine_prices:
                price = mine_prices[mine_name]
                
                if user_data["balance"] >= price:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(f"Купить за {price} $", callback_data=f"buy_mine_{mine_name}"))
                    
                    bot.send_message(
                        message.chat.id, 
                        f"🔒 Шахта *{mine_name}* закрыта. Цена покупки: *{price} $*",
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                else:
                    bot.send_message(
                        message.chat.id, 
                        f"🔒 Шахта *{mine_name}* закрыта. Цена покупки: *{price} $*\n\nУ вас недостаточно средств!",
                        parse_mode="Markdown"
                    )

    # Обработка кнопки "Профиль"
    elif "Профиль" in message.text:
        user_current_menu[user_id] = "profile"  # Добавим отслеживание меню профиля
        
        profile_text = (
            f"*👤 Профиль:*\n\n"
            f"📝 *Никнейм:* {message.from_user.username or message.from_user.first_name}\n"
            f"💰 *Баланс:* {user_data['balance']}$\n"
            f"⛏ *Уровень кирки:* {user_data['pickaxe_level']}/50\n"
            f"🏭 *Уровень шахты:* {user_data['mine_level']}/10\n"
            f"🌳 *Лучшая шахта:* {get_best_mine(user_data['mines_unlocked'])}\n\n"
            f"*💲 Ресурсы:*\n"
        )
        
        # Добавляем эмодзи для всех ресурсов, включая уголь
        for resource, amount in user_data["resources"].items():
            if resource == "земля":
                emoji = "🟤"
            elif resource == "дерево":
                emoji = "🟢"
            elif resource == "камень":
                emoji = "⚪"
            elif resource == "уголь":
                emoji = "⚫"
            else:
                emoji = "🔹"
            profile_text += f"{emoji} {resource.capitalize()}: {amount}\n"
        
        bot.send_message(message.chat.id, profile_text, parse_mode="Markdown", reply_markup=profile_menu())

    # Обработка кнопки продажи земли
    elif message.text == "Продать землю":
        amount = user_data["resources"]["земля"]
        price = resource_prices["земля"]
        total_price = amount * price
        
        user_data["balance"] += total_price
        user_data["resources"]["земля"] = 0
        update_user_data(user_id, user_data)
        
        bot.send_message(
            message.chat.id,
            f"✅ Продано *{amount}* земли за *{total_price}$*",
            parse_mode="Markdown",
            reply_markup=sell_menu(user_data)
        )
    
    # Обработка кнопки продажи дерева
    elif message.text == "Продать дерево":
        amount = user_data["resources"]["дерево"]
        price = resource_prices["дерево"]
        total_price = amount * price
        
        user_data["balance"] += total_price
        user_data["resources"]["дерево"] = 0
        update_user_data(user_id, user_data)
        
        bot.send_message(
            message.chat.id,
            f"✅ Продано *{amount}* дерева за *{total_price}$*",
            parse_mode="Markdown",
            reply_markup=sell_menu(user_data)
        )
    
    # Обработка кнопки продажи камня
    elif message.text == "Продать камень":
        amount = user_data["resources"]["камень"]
        price = resource_prices["камень"]
        total_price = amount * price
        
        user_data["balance"] += total_price
        user_data["resources"]["камень"] = 0
        update_user_data(user_id, user_data)
        
        bot.send_message(
            message.chat.id,
            f"✅ Продано *{amount}* камня за *{total_price}$*",
            parse_mode="Markdown",
            reply_markup=sell_menu(user_data)
        )
    
    # Обработка кнопки продажи угля
    elif message.text == "Продать уголь":
        amount = user_data["resources"]["уголь"]
        price = resource_prices["уголь"]
        total_price = amount * price
        
        user_data["balance"] += total_price
        user_data["resources"]["уголь"] = 0
        update_user_data(user_id, user_data)
        
        bot.send_message(
            message.chat.id,
            f"✅ Продано *{amount}* угля за *{total_price}$*",
            parse_mode="Markdown",
            reply_markup=sell_menu(user_data)
        )
    
    # Обработка кнопки "Продать всё"
    elif message.text == "Продать всё":
        total_earned = 0
        resources_sold = []
        
        for resource, amount in user_data["resources"].items():
            if amount > 0:
                price = resource_prices[resource]
                total_price = amount * price
                total_earned += total_price
                
                emoji = "🟤" if resource == "земля" else "🟢" if resource == "дерево" else "⚪" if resource == "камень" else "⚫"
                resources_sold.append(f"{emoji} {amount} {resource} за {total_price}$")
                
                user_data["resources"][resource] = 0
        
        user_data["balance"] += total_earned
        update_user_data(user_id, user_data)
        
        # Формируем сообщение о продаже
        sell_text = "✅ *Ресурсы проданы:*\n\n"
        sell_text += "\n".join(resources_sold)
        sell_text += f"\n\n💰 *Всего получено:* {total_earned}$"
        
        bot.send_message(
            message.chat.id,
            sell_text,
            parse_mode="Markdown",
            reply_markup=sell_menu(user_data)
        )

# Обработка команды /help
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "*📜 Правила игры:*\n\n"
        "1. ⛏ *Шахта:*\n"
        "   - Добывайте ресурсы: землю, дерево, камень и уголь\n"
        "   - Улучшайте кирку и шахту для повышения добычи\n"
        "   - Покупайте новые шахты для доступа к более ценным ресурсам\n\n"
        "2. 📋 *Меню:*\n"
        "   - Улучшайте кирку до 50 уровня для увеличения эффективности\n"
        "   - Получайте ежедневные бонусы\n"
        "   - Продавайте ресурсы за деньги\n"
        "   - Выполняйте задания для получения наград\n\n"
        "3. 🔨 *Улучшения:*\n"
        "   - Кирка: улучшайте кирку до 50 уровня, каждый уровень уменьшает таймаут на 0.3 секунды\n"
        "   - Шахта: улучшайте шахту до 10 уровня, каждый уровень увеличивает добычу на +1 ресурс\n\n"
        "4. 📋 *Задания:*\n"
        "   - Выполняйте задания на добычу разных видов ресурсов\n"
        "   - За каждое выполненное задание вы получаете денежную награду\n\n"
        "5. 💰 *Продажа:*\n"
        "   - Продавайте ресурсы за деньги: земля - 1$, дерево - 3$, камень - 5$, уголь - 8$\n\n"
        "6. 🎁 *Бонус:*\n"
        "   - Получайте ежедневный бонус от 3 до 10 долларов\n\n"
        "*Удачи в игре!* 🎮"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Обработка callback-запросов от inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    
    # Покупка шахты
    if call.data.startswith("buy_mine_"):
        mine_name = call.data[9:]  # Получаем название шахты после "buy_mine_"
        
        if mine_name in mine_prices:
            price = mine_prices[mine_name]
            
            if user_data["balance"] >= price:
                user_data["balance"] -= price
                user_data["mines_unlocked"].append(mine_name)
                
                # При покупке обновляем current_mine только если новая шахта лучше текущей
                current_index = mines_order.index(user_data["current_mine"]) if user_data["current_mine"] in mines_order else 0
                new_index = mines_order.index(mine_name)
                
                if new_index > current_index:
                    user_data["current_mine"] = mine_name
                
                update_user_data(user_id, user_data)
                
                bot.answer_callback_query(call.id, f"✅ Шахта {mine_name} куплена!")
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"✅ Вы успешно приобрели шахту *{mine_name}*!",
                    parse_mode="Markdown"
                )
                
                # Обновляем меню шахт
                bot.send_message(
                    call.message.chat.id,
                    "Выберите шахту для добычи ресурсов:",
                    reply_markup=mines_menu(user_data)
                )
            else:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств для покупки!", show_alert=True)

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)

