import time
import re
import random
import requests
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
first_start = True  # Флаг для первого запуска


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
        
        print("🔄 Нажимаем 'Узнать курс'...")
        learn_data = {
            'act': 'item',
            'id': '14069',
            'program': '51164l9l1809791bb20cc8f8',
            'action': 'learn'
        }
        session.post(APP_URL, data=learn_data, headers=headers)
        time.sleep(1)
        
        print("🔄 Нажимаем 'Обновить курс'...")
        update_data = {
            'act': 'item',
            'id': '14069',
            'action': 'update'
        }
        session.post(APP_URL, data=update_data, headers=headers)
        time.sleep(1)
        
        print("📥 Получаем страницу с курсом...")
        response = session.get(APP_URL, headers=headers)
        response.raise_for_status()
        
        html = response.text
        
        print(f"📄 HTML получен, длина: {len(html)}")
        
        # --- ИЩЕМ КУРС ---
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)[^0-9]*=>[^0-9]*([0-9]+)', html)
        sell_match = re.search(r'Продажа[^0-9]*([0-9]+)[^0-9]*=>[^0-9]*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(2))
            print(f"✅ Найден курс (вариант 1): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
        sell_match = re.search(r'Продажа[^0-9]*100[^0-9]*=>[^0-9]*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            print(f"✅ Найден курс (вариант 2): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        numbers = re.findall(r'\b([5-7][0-9]{4})\b', html)
        if len(numbers) >= 2:
            buy_rate = int(numbers[0])
            sell_rate = int(numbers[1])
            print(f"✅ Найден курс (вариант 3): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        lines = html.split('\n')
        buy_rate = None
        sell_rate = None
        
        for line in lines:
            if 'Покупка' in line:
                nums = re.findall(r'\b([0-9]+)\b', line)
                if nums:
                    buy_rate = int(nums[0])
                    print(f"   Найдена покупка: {buy_rate}")
            if 'Продажа' in line:
                nums = re.findall(r'\b([0-9]+)\b', line)
                if len(nums) >= 2:
                    sell_rate = int(nums[1])
                    print(f"   Найдена продажа: {sell_rate}")
        
        if buy_rate and sell_rate:
            print(f"✅ Найден курс (вариант 4): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        print("⚠️ Курс не найден на странице")
        return None, None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None, None


def check_conditions(buy_rate, sell_rate):
    """Проверяет условия (остаётся в коде, но не показывается пользователю)"""
    return buy_rate < BUY_THRESHOLD or sell_rate > SELL_THRESHOLD


def get_notification_interval(notification_count):
    return 5 if notification_count < 2 else 10


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def main():
    global update_count, notification_count, last_alive_time, first_start

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

    # --- ПЕРВОЕ СООБЩЕНИЕ ПРИ ЗАПУСКЕ ---
    if first_start:
        start_message = (
            f"🚀 БОТ ЗАПУЩЕН И РАБОТАЕТ!\n"
            f"\n"
            f"📊 Отслеживание курса осколков\n"
            f"🟢 Покупка: ниже {BUY_THRESHOLD}\n"
            f"🔴 Продажа: выше {SELL_THRESHOLD}\n"
            f"\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        send_vk_message(start_message)
        first_start = False
        print("💚 Отправлено сообщение о запуске бота")

    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка курса...")
            
            buy_rate, sell_rate = get_rate_from_web()

            if buy_rate and sell_rate:
                update_count += 1
                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

                # --- ПРОВЕРКА "ЖИВ ЛИ БОТ" КАЖДЫЙ ЧАС ---
                current_time = time.time()
                if current_time - last_alive_time >= 3600:
                    alive_message = (
                        f"✅ Бот жив и работает!\n"
                        f"\n"
                        f"📊 Проверок: {update_count}\n"
                        f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                        f"🔴 Продажа: 100 => {sell_rate} оск.\n"
                        f"\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    send_vk_message(alive_message)
                    last_alive_time = current_time
                    print(f"💚 Отправлено сообщение о жизни бота")

                # --- ПРОВЕРКА УСЛОВИЙ ---
                if check_conditions(buy_rate, sell_rate):
                    notification_count += 1
                    print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")

                    current_interval = get_notification_interval(notification_count)
                    current_time = time.time()

                    if current_time - last_notification_time >= current_interval:
                        # --- ОТПРАВКА СООБЩЕНИЯ БЕЗ УСЛОВИЙ ---
                        message = (
                            f"🚨 ВЫГОДНЫЙ КУРС ОСКОЛКОВ! 🚨\n"
                            f"\n"
                            f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                            f"🔴 Продажа: 100 => {sell_rate} оск.\n"
                            f"\n"
                            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                        )

                        send_vk_message(message)
                        last_notification_time = current_time
                        print(f"📊 Следующее уведомление через {get_notification_interval(notification_count)} сек")
                else:
                    print(f"⏳ Условия не выполнены:")
                    print(f"   Покупка {buy_rate} >= {BUY_THRESHOLD} или Продажа {sell_rate} <= {SELL_THRESHOLD}")
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
