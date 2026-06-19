import time
import re
import random
import requests
from datetime import datetime
import vk_api
from vk_api.utils import get_random_id

# --- НАСТРОЙКИ ---
GROUP_TOKEN = "vk1.a.8Gc4tpdnYrLN_BRQ1puFlBBWac3X6AivdJGP2S5pNsVIspW2kfn4dWV6nmFh_X8TWKkZm9yzST751CQFdJ84-J30Uq_T_sFoRshtOlgLDlUZ97VAzgDcoj1jh5s5j6ExbTEcNAmNqhgGo6MpjPf8WIPNbyULTIazIJhyLThAHLx8EyLAjyh9Ya8wNrYRK_jyiTqckSnoDHPutcJOk8khpg"

USER_IDS = [
    212887447,
    145156004,
]

BUY_THRESHOLD = 70000
SELL_THRESHOLD = 60000

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

MIN_CHECK_INTERVAL = 5
MAX_CHECK_INTERVAL = 13

# --- ИНИЦИАЛИЗАЦИЯ VK ---
vk_session = vk_api.VkApi(token=GROUP_TOKEN)
vk = vk_session.get_api()

update_count = 0
notification_count = 0


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
    """Получает курс через HTTP-запрос с нажатием кнопок"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Создаём сессию для сохранения кук
        session = requests.Session()
        
        # 1. Переходим на страницу
        print("🌐 Переходим на страницу...")
        session.get(APP_URL, headers=headers)
        time.sleep(1)
        
        # 2. НАЖИМАЕМ КНОПКУ "Узнать курс"
        print("🔄 Нажимаем 'Узнать курс'...")
        learn_data = {
            'act': 'item',
            'id': '14069',
            'action': 'learn'
        }
        session.post(APP_URL, data=learn_data, headers=headers)
        time.sleep(1)
        
        # 3. НАЖИМАЕМ КНОПКУ "Обновить курс"
        print("🔄 Нажимаем 'Обновить курс'...")
        update_data = {
            'act': 'item',
            'id': '14069',
            'action': 'update'
        }
        session.post(APP_URL, data=update_data, headers=headers)
        time.sleep(1)
        
        # 4. Получаем страницу с обновлённым курсом
        print("📥 Получаем страницу с курсом...")
        response = session.get(APP_URL, headers=headers)
        response.raise_for_status()
        
        html = response.text
        
        # Сохраняем HTML для отладки
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("📄 Сохранён debug.html")
        
        # Ищем курс
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)\s*=>', html)
        sell_match = re.search(r'Продажа[^0-9]*100\s*=>\s*[^0-9]*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            print(f"✅ Найден курс: покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        # Альтернативный поиск
        buy_match = re.search(r'Покупка:\s*([0-9]+)', html)
        sell_match = re.search(r'Продажа:\s*100\s*=>\s*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            print(f"✅ Найден курс (альт): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        print("⚠️ Курс не найден на странице")
        return None, None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None, None


def check_conditions(buy_rate, sell_rate):
    return buy_rate < BUY_THRESHOLD or sell_rate > SELL_THRESHOLD


def get_condition_text(buy_rate, sell_rate):
    conditions = []
    conditions.append(f"{'✅' if buy_rate < BUY_THRESHOLD else '❌'} Покупка {buy_rate} {'<' if buy_rate < BUY_THRESHOLD else '>='} {BUY_THRESHOLD}")
    conditions.append(f"{'✅' if sell_rate > SELL_THRESHOLD else '❌'} Продажа {sell_rate} {'>' if sell_rate > SELL_THRESHOLD else '<='} {SELL_THRESHOLD}")
    return "\n".join(conditions)


def get_notification_interval(notification_count):
    return 5 if notification_count < 2 else 10


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def main():
    global update_count, notification_count

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

    last_notification_time = 0

    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка курса...")
            
            buy_rate, sell_rate = get_rate_from_web()

            if buy_rate and sell_rate:
                update_count += 1
                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

                if check_conditions(buy_rate, sell_rate):
                    notification_count += 1
                    print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")
                    print(f"   {get_condition_text(buy_rate, sell_rate)}")

                    current_interval = get_notification_interval(notification_count)
                    current_time = time.time()

                    if current_time - last_notification_time >= current_interval:
                        message = (
                            f"🚨 ВЫГОДНЫЙ КУРС ОСКОЛКОВ! 🚨\n"
                            f"\n"
                            f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                            f"🔴 Продажа: 100 => {sell_rate} оск.\n"
                            f"\n"
                            f"📊 УСЛОВИЯ:\n"
                            f"   {'✅' if buy_rate < BUY_THRESHOLD else '❌'} Покупка {buy_rate} {'<' if buy_rate < BUY_THRESHOLD else '>='} {BUY_THRESHOLD}\n"
                            f"   {'✅' if sell_rate > SELL_THRESHOLD else '❌'} Продажа {sell_rate} {'>' if sell_rate > SELL_THRESHOLD else '<='} {SELL_THRESHOLD}\n"
                            f"\n"
                            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                        )

                        send_vk_message(message)
                        last_notification_time = current_time
                        print(f"📊 Следующее уведомление через {get_notification_interval(notification_count)} сек")
                else:
                    print(f"⏳ Условия не выполнены:")
                    print(f"   {get_condition_text(buy_rate, sell_rate)}")
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
