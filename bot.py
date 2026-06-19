import time
import re
import random
import requests
import os
import pickle
from datetime import datetime
import vk_api
from vk_api.utils import get_random_id

print("🚀 Бот запускается...")

# --- НАСТРОЙКИ ---
GROUP_TOKEN = "vk1.a.8Gc4tpdnYrLN_BRQ1puFlBBWac3X6AivdJGP2S5pNsVIspW2kfn4dWV6nmFh_X8TWKkZm9yzST751CQFdJ84-J30Uq_T_sFoRshtOlgLDlUZ97VAzgDcoj1jh5s5j6ExbTEcNAmNqhgGo6MpjPf8WIPNbyULTIazIJhyLThAHLx8EyLAjyh9Ya8wNrYRK_jyiTqckSnoDHPutcJOk8khpg"

USER_IDS = [
    212887447,
    145156004,
]

BUY_THRESHOLD = 50000
SELL_THRESHOLD = 60000

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

MIN_CHECK_INTERVAL = 5
MAX_CHECK_INTERVAL = 13

STATE_FILE = "bot_state.pkl"

print("📌 Настройки загружены")

# --- ИНИЦИАЛИЗАЦИЯ VK ---
try:
    vk_session = vk_api.VkApi(token=GROUP_TOKEN)
    vk = vk_session.get_api()
    print("✅ VK API инициализирован")
except Exception as e:
    print(f"❌ Ошибка инициализации VK: {e}")
    exit(1)

update_count = 0
notification_count = 0
last_alive_time = time.time()


def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                return pickle.load(f)
        return {"first_start_done": False, "alive_count": 0}
    except:
        return {"first_start_done": False, "alive_count": 0}


def save_state(state):
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump(state, f)
    except:
        pass


def send_vk_message(text):
    success_count = 0
    fail_count = 0
    for user_id in USER_IDS:
        try:
            vk.messages.send(
                user_id=user_id,
                random_id=get_random_id(),
                message=text
            )
            print(f"   ✅ Отправлено пользователю {user_id}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Ошибка отправки пользователю {user_id}: {e}")
            fail_count += 1
    print(f"📊 Итог: успешно {success_count}, ошибок {fail_count}")
    return success_count > 0


def get_rate_from_web():
    """Получает курс через HTTP-запрос с имитацией кнопок"""
    try:
        print("🌐 Начинаем запрос...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        session = requests.Session()
        
        print("🌐 Переходим на страницу...")
        session.get(APP_URL, headers=headers)
        time.sleep(1)
        
        print("🔄 Нажимаем 'Обновить курс'...")
        update_data = {
            'act': 'item',
            'id': '14069',
            'action': 'update'
        }
        session.post(APP_URL, data=update_data, headers=headers)
        time.sleep(2)
        
        print("📥 Получаем страницу с курсом...")
        response = session.get(APP_URL, headers=headers)
        response.raise_for_status()
        
        html = response.text
        
        print(f"📄 HTML получен, длина: {len(html)}")
        
        # --- ПАРСИМ КУРС ---
        # Ищем "Покупка: 🌕59873 => 💎100"
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)[^0-9]*=>[^0-9]*100', html)
        sell_match = re.search(r'Продажа[^0-9]*100[^0-9]*=>[^0-9]*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            print(f"✅ Найден курс: покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        # Способ 2: Ищем в блоке program_chat
        chat_match = re.search(r'<div class="program_chat">.*?Покупка[^0-9]*([0-9]+).*?Продажа[^0-9]*([0-9]+)', html, re.DOTALL)
        if chat_match:
            buy_rate = int(chat_match.group(1))
            sell_rate = int(chat_match.group(2))
            print(f"✅ Найден курс (способ 2): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        print("⚠️ Курс не найден на странице")
        return None, None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None, None


def check_conditions(buy_rate, sell_rate):
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    return buy_condition or sell_condition


def get_notification_interval(notification_count):
    return 5 if notification_count < 2 else 10


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def main():
    global update_count, notification_count, last_alive_time

    print("🤖 Бот для отслеживания курса осколков")
    print("=" * 60)
    print(f"📱 Получателей: {len(USER_IDS)}")
    print("=" * 60)
    print("📊 УСЛОВИЯ ДЛЯ УВЕДОМЛЕНИЯ (ХОТЯ БЫ ОДНО):")
    print(f"   1️⃣ Покупка должна быть НИЖЕ {BUY_THRESHOLD}")
    print(f"   2️⃣ Продажа должна быть ВЫШЕ {SELL_THRESHOLD}")
    print("=" * 60)
    print("📢 ИНТЕРВАЛЫ ПРОВЕРКИ:")
    print(f"   - Случайная задержка {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} секунд")
    print("=" * 60)
    print("💚 Сообщение 'Бот жив' будет приходить раз в час")
    print("=" * 60)

    last_notification_time = 0

    state = load_state()
    first_start_done = state.get("first_start_done", False)
    alive_count = state.get("alive_count", 0)

    if not first_start_done:
        start_message = (
            f"🚀 БОТ ЗАПУЩЕН И РАБОТАЕТ!\n"
            f"\n"
            f"📊 Отслеживание курса осколков\n"
            f"🟢 Покупка: ниже {BUY_THRESHOLD}\n"
            f"🔴 Продажа: выше {SELL_THRESHOLD}"
        )
        send_vk_message(start_message)
        state["first_start_done"] = True
        save_state(state)
        print("💚 Отправлено сообщение о запуске бота (первый и единственный раз)")

    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка курса...")
            
            buy_rate, sell_rate = get_rate_from_web()

            if buy_rate and sell_rate:
                update_count += 1
                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

                current_time = time.time()
                if current_time - last_alive_time >= 3600:
                    alive_count += 1
                    state = load_state()
                    state["alive_count"] = alive_count
                    save_state(state)
                    
                    alive_message = (
                        f"✅ Бот жив и работает!\n"
                        f"\n"
                        f"📊 Проверок: {update_count}\n"
                        f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                        f"🔴 Продажа: 100 => {sell_rate} оск."
                    )
                    send_vk_message(alive_message)
                    last_alive_time = current_time
                    print(f"💚 Отправлено сообщение о жизни бота (#{alive_count})")

                conditions_met = check_conditions(buy_rate, sell_rate)
                print(f"📋 Условия: Покупка {buy_rate} < {BUY_THRESHOLD} = {buy_rate < BUY_THRESHOLD}, Продажа {sell_rate} > {SELL_THRESHOLD} = {sell_rate > SELL_THRESHOLD}")
                print(f"📋 Результат: {'✅ ВЫПОЛНЕНЫ' if conditions_met else '❌ НЕ ВЫПОЛНЕНЫ'}")
                
                if conditions_met:
                    notification_count += 1
                    print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")

                    current_interval = get_notification_interval(notification_count)
                    current_time = time.time()

                    if current_time - last_notification_time >= current_interval:
                        message = (
                            f"🚨 ВЫГОДНЫЙ КУРС ОСКОЛКОВ! 🚨\n"
                            f"\n"
                            f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                            f"🔴 Продажа: 100 => {sell_rate} оск."
                        )

                        send_vk_message(message)
                        last_notification_time = current_time
                        print(f"📊 Следующее уведомление через {get_notification_interval(notification_count)} сек")
                    else:
                        wait_time = int(current_interval - (current_time - last_notification_time))
                        print(f"⏳ Ожидаем {wait_time} сек перед следующим уведомлением")
                else:
                    print(f"⏳ Условия не выполнены — сообщение НЕ отправлено")
            else:
                print("❌ Не удалось получить курс")

            delay = get_random_delay()
            print(f"⏳ Следующая проверка через {delay} секунд...")
            time.sleep(delay)

        except KeyboardInterrupt:
            print("\n⏹ Остановка...")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(get_random_delay())


if __name__ == "__main__":
    main()
