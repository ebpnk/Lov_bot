import telebot
from telebot import types
import json

TOKEN = "Сюда токен бота"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "sessions_data.json"
sessions = {}
waiting_users = []
user_interests = {}
INTERESTS = ['🎙Музыка', '🎥Кино', '📚Книги', '🎖Спорт', '🔋Технологии', '🗿Искусство', '🔞18+']

try:
    with open(DATA_FILE, "r") as file:
        data = json.load(file)
        sessions = data.get("sessions", {})
        waiting_users = data.get("waiting_users", [])
        user_interests = data.get("user_interests", {})
except FileNotFoundError:
    pass

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    update_markup(user_id)
    update_interests_message(user_id)

@bot.message_handler(commands=['new'])
def handle_new_command(message):
    handle_switch(message)

@bot.message_handler(commands=['stop'])
def handle_stop_command(message):
    handle_end(message)

@bot.message_handler(commands=['off'])
def handle_off_command(message):
    stop_search(message)

@bot.message_handler(commands=['on'])
def handle_on_command(message):
    handle_search(message)    

def update_markup(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    text = "Выберите опцию:"
    if user_id in sessions:
        markup.add(types.KeyboardButton('🔄 Сменить собеседника'), types.KeyboardButton('❌ Завершить разговор'))
        text += " /new новый, /stop стоп"
    elif user_id in waiting_users:
        markup.add(types.KeyboardButton('🛑 Прекратить поиск'))
        text += " /off прекратить поиск"
    else:
        markup.add(types.KeyboardButton('🔍 Искать собеседника'), types.KeyboardButton('📝 Профиль'))
        text += " /on искать собеседника"

    bot.send_message(user_id, text, reply_markup=markup)

user_interests_message_ids = {}

    

@bot.message_handler(func=lambda message: message.text == '📝 Профиль' or message.text == '/change_interests')
def handle_profile_command(message):
    user_id = message.chat.id
    handle_profile(user_id)

def handle_profile(user_id):
    markup = types.InlineKeyboardMarkup()
    for interest in INTERESTS:
        if interest in user_interests.get(user_id, []):
            continue  # Skip interests already selected
        markup.add(types.InlineKeyboardButton(interest, callback_data=f"interest_{interest}"))
    markup.add(types.InlineKeyboardButton('Сохранить интересы', callback_data="save_interests"))
    # Add a button to allow users to change their interests
    markup.add(types.InlineKeyboardButton('Изменить интересы', callback_data="change_interests"))
    bot.send_message(user_id, "Выберите ваши интересы:", reply_markup=markup)

# Add a callback handler for changing interests
@bot.callback_query_handler(func=lambda call: call.data == "change_interests")
def change_interests(call):
    user_id = call.message.chat.id
    # Reset previously selected interests
    user_interests[user_id] = []
    # Trigger the interest selection process again
    handle_profile(user_id) 

@bot.callback_query_handler(func=lambda call: call.data.startswith("interest_"))
def handle_interest_selection(call):
    user_id = call.message.chat.id
    interest = call.data.split("_")[1]
    
    if user_id not in user_interests:
        user_interests[user_id] = []
        
    if interest not in user_interests[user_id]:
        if len(user_interests[user_id]) < 3:  # Позволяет выбрать не более трех интересов
            user_interests[user_id].append(interest)
            bot.send_message(user_id, f"Вы выбрали интерес: {interest}")
        else:
            bot.send_message(user_id, "Вы уже выбрали максимальное количество интересов.")
        
        # Обновляем сообщение с выбором интересов и меню выбора
        update_interests_message(user_id)

def update_interests_message(user_id):
    if user_id in user_interests_message_ids:
        message_id = user_interests_message_ids[user_id]
        markup = types.InlineKeyboardMarkup()
        for interest in INTERESTS:
            if interest in user_interests.get(user_id, []):
                continue  # Интерес уже выбран
            markup.add(types.InlineKeyboardButton(interest, callback_data=f"interest_{interest}"))
        markup.add(types.InlineKeyboardButton('Сохранить интересы', callback_data="save_interests"))
        try:
            bot.edit_message_text(chat_id=user_id, message_id=message_id,
                                  text="Выберите ваши интересы:", reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Failed to edit message: {e}")


@bot.callback_query_handler(func=lambda call: call.data == "save_interests")
def save_interests(call):
    user_id = call.message.chat.id
    bot.send_message(user_id, f"Ваши интересы сохранены: {', '.join(user_interests.get(user_id, []))}")
    update_markup(user_id)

@bot.message_handler(func=lambda message: message.text in ['🔍 Искать собеседника', '🔍 Профиль'])
def handle_commands(message):
    if message.text == '🔍 Профиль':
        handle_profile(message)
    elif message.text == '🔍 Искать собеседника':
        handle_search(message)

@bot.message_handler(func=lambda message: message.text == '🔍 Искать собеседника')
def handle_search(message):
    user_id = message.chat.id
    if user_id in sessions:
        bot.send_message(user_id, "Вы уже общаетесь. Используйте '🔄 Сменить собеседника' или '❌ Завершить разговор'.")
    elif user_id in waiting_users:
        bot.send_message(user_id, "Вы уже находитесь в списке ожидания.")
    else:
        waiting_users.append(user_id)
        update_markup(user_id)
        bot.send_message(user_id, "Вы добавлены в список ожидания. Идет поиск собеседника...")
        if len(waiting_users) >= 2:
            connect_users()

@bot.message_handler(func=lambda message: message.text == '🛑 Прекратить поиск')
def stop_search(message):
    user_id = message.chat.id
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        bot.send_message(user_id, "Поиск прекращен.")
        update_markup(user_id)

@bot.message_handler(func=lambda message: message.text == '🔄 Сменить собеседника')
def handle_switch(message):
    user_id = message.chat.id
    if user_id in sessions:
        partner_id = sessions.pop(user_id)
        sessions.pop(partner_id, None)
        waiting_users.extend([user_id, partner_id])
        bot.send_message(partner_id, "Ваш собеседник решил сменить собеседника.")
        bot.send_message(user_id, "Вы решили сменить собеседника.")
        connect_users()
    else:
        bot.send_message(user_id, "Вы не общаетесь сейчас, чтобы сменить собеседника.")

@bot.message_handler(func=lambda message: message.text == '❌ Завершить разговор')
def handle_end(message):
    user_id = message.chat.id
    end_conversation(user_id)

def end_conversation(user_id):
    if user_id in sessions:
        partner_id = sessions.pop(user_id)
        sessions.pop(partner_id, None)
        bot.send_message(user_id, "Разговор завершен. Вы можете начать новый поиск.")
        bot.send_message(partner_id, "Ваш собеседник завершил разговор. Вы будете автоматически добавлены в поиск нового собеседника.")
        update_markup(user_id)
        waiting_users.append(partner_id)
        update_markup(partner_id)
        if len(waiting_users) >= 2:
            connect_users()
    else:
        bot.send_message(user_id, "Вы не в разговоре, чтобы его завершить.")
        update_markup(user_id)

@bot.message_handler(func=lambda message: message.chat.id in sessions and message.text)
def relay_message(message):
    sender_id = message.chat.id
    receiver_id = sessions[sender_id]
    bot.send_message(receiver_id, message.text)
    print(f"Переслано сообщение от {sender_id} к {receiver_id}: {message.text}")

def connect_users():
    while len(waiting_users) > 1:
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)
        sessions[user1] = user2
        sessions[user2] = user1
        interests_user1 = ', '.join(user_interests.get(user1, []))
        interests_user2 = ', '.join(user_interests.get(user2, []))
        try:
            bot.send_message(user1, f"Собеседник найден! Интересы собеседника: {interests_user2}")
            bot.send_message(user2, f"Собеседник найден! Интересы собеседника: {interests_user1}")
            update_markup(user1)
            update_markup(user2)
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")

def save_data():
    data = {"sessions": sessions, "waiting_users": waiting_users, "user_interests": user_interests}
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

import atexit
atexit.register(save_data)

bot.polling(non_stop=True)
