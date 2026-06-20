import time
import re
import pickle
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import vk_api
from vk_api.utils import get_random_id
from webdriver_manager.chrome import ChromeDriverManager

print("🚀 Бот запускается...")

# --- НАСТРОЙКИ ---
GROUP_TOKEN = "vk1.a.AmFPbkY4T9acuaWmLC1gQYNU3DqhZpS1PR1CMlSR7GV36ryU7ogRz2URrgnXYGZYYm_h0SQBhy71_5AG5HcIb3csegaBnks_1PweRiC20t5Im-hfbhkZnVNykMmFJBEbzPZ52WoJWzXPPZYXwa1_wJfxmtfmd86W7OcBSMuK2AGCYsJO97g6MB5pPhLRYJVE_KFBO9lK0JpfeiPPy9aRSg"

# --- ПОЛУЧАТЕЛИ ---
ADMIN_ID = 212887447  # Только этот пользователь получает "Бот жив"
USER_IDS = [
    212887447,
    145156004,
    816395698,
    459341710,
]

BUY_THRESHOLD = 50000
SELL_THRESHOLD = 60000

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

# --- АДАПТИВНЫЕ ИНТЕРВАЛЫ ---
FAST_CHECK_TIMES = 3
FAST_CHECK_INTERVAL = 3
NORMAL_CHECK_INTERVAL = 5
MIN_CHECK_INTERVAL = 5
MAX_CHECK_INTERVAL = 10

# --- "БОТ ЖИВ" — 5-10 МИНУТ (ТОЛЬКО АДМИНУ) ---
MIN_ALIVE_INTERVAL = 300   # 5 минут
MAX_ALIVE_INTERVAL = 600   # 10 минут

# --- МИНИМАЛЬНАЯ ЗАДЕРЖКА МЕЖДУ УВЕДОМЛЕНИЯМИ ---
NOTIFICATION_INTERVAL = 1

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
last_notification_time = 0
fast_check_counter = 0
was_profitable = False


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


def send_vk_message_to_admin(text):
    """Отправляет сообщение ТОЛЬКО админу"""
    try:
        vk.messages.send(
            user_id=ADMIN_ID,
            random_id=get_random_id(),
            message=text
        )
        print(f"   ✅ Отправлено админу {ADMIN_ID}")
        return True
    except Exception as e:
        print(f"   ❌ Ошибка отправки админу: {e}")
        return False


def send_vk_message_to_all(text):
    """Отправляет сообщение ВСЕМ пользователям"""
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


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--memory-pressure-off")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ Драйвер создан")
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        raise


def clear_browser_data(driver):
    try:
        driver.delete_all_cookies()
        print("   🗑️ Куки удалены")
    except:
        pass
    try:
        driver.execute_script("window.localStorage.clear();")
        print("   🗑️ LocalStorage очищен")
    except:
        pass
    try:
        driver.execute_script("window.sessionStorage.clear();")
        print("   🗑️ SessionStorage очищен")
    except:
        pass


def parse_rate_from_html(html):
    buy_rate = None
    sell_rate = None
    
    buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
    if buy_match:
        buy_rate = int(buy_match.group(1))
        print(f"   Покупка: {buy_rate}")
    
    sell_match = re.search(r'Продажа[^0-9]*💎100[^0-9]*=>?[^0-9]*🌕([0-9]+)', html)
    if sell_match:
        sell_rate = int(sell_match.group(1))
        print(f"   Продажа: {sell_rate}")
    
    if not sell_rate:
        sell_match = re.search(r'Продажа[^0-9]*=>[^0-9]*([0-9]+)', html)
        if sell_match:
            sell_rate = int(sell_match.group(1))
            print(f"   Продажа (упрощ.): {sell_rate}")
    
    if buy_rate and sell_rate:
        return buy_rate, sell_rate
    
    if buy_rate:
        return buy_rate, 0
    
    return None, None


def check_conditions(buy_rate, sell_rate):
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    result = buy_condition or sell_condition
    print(f"   📋 Проверка условий: покупка {buy_rate} < {BUY_THRESHOLD} = {buy_condition}, продажа {sell_rate} > {SELL_THRESHOLD} = {sell_condition}, результат: {result}")
    return result


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def get_random_alive_interval():
    """Возвращает случайное время от 5 до 10 минут (в секундах)"""
    return random.randint(MIN_ALIVE_INTERVAL, MAX_ALIVE_INTERVAL)


def get_check_delay(is_profitable, fast_check_counter):
    if is_profitable:
        if fast_check_counter < FAST_CHECK_TIMES:
            return FAST_CHECK_INTERVAL
        else:
            return NORMAL_CHECK_INTERVAL
    else:
        return get_random_delay()


def check_rate_once():
    driver = None
    try:
        driver = get_driver()
        
        print("🌐 Открываем страницу...")
        driver.get(APP_URL)
        time.sleep(2)
        
        print("🔄 Нажимаем 'Узнать курс'...")
        try:
            learn_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Узнать курс')]")
            learn_btn.click()
            print("   ✅ Нажата кнопка 'Узнать курс'")
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Кнопка 'Узнать курс' не найдена: {e}")
        
        print("🔄 Нажимаем 'Обновить курс'...")
        try:
            update_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Обновить курс')]")
            update_btn.click()
            print("   ✅ Нажата кнопка 'Обновить курс'")
            time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ Кнопка 'Обновить курс' не найдена: {e}")
        
        html = driver.page_source
        print(f"📄 HTML получен, длина: {len(html)}")
        
        clear_browser_data(driver)
        
        return parse_rate_from_html(html)
        
    except Exception as e:
        print(f"❌ Ошибка в check_rate_once: {e}")
        return None, None
    finally:
        if driver:
            try:
                driver.quit()
                print("✅ Браузер закрыт")
            except:
                pass


def main():
    global update_count, notification_count, last_alive_time, last_notification_time, fast_check_counter, was_profitable

    print("🤖 Бот для отслеживания курса осколков")
    print("=" * 60)
    print(f"📱 Админ (получает 'Бот жив'): {ADMIN_ID}")
    print(f"📱 Получатели уведомлений: {USER_IDS}")
    print("=" * 60)
    print("📊 УСЛОВИЯ (ИЛИ):")
    print(f"   1️⃣ Покупка < {BUY_THRESHOLD}")
    print(f"   2️⃣ Продажа > {SELL_THRESHOLD}")
    print("=" * 60)
    print("📢 АДАПТИВНЫЕ ИНТЕРВАЛЫ ПРОВЕРКИ:")
    print(f"   - При выгодном курсе: 3 сек (первые 3 раза), затем 5 сек")
    print(f"   - При обычном курсе: случайно {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек")
    print("=" * 60)
    print(f"📢 'Бот жив' — ТОЛЬКО АДМИНУ, каждые 5-10 минут")
    print(f"📢 Уведомления о курсе — ВСЕМ пользователям")
    print("=" * 60)

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
        send_vk_message_to_admin(start_message)
        state["first_start_done"] = True
        save_state(state)
        print("💚 Отправлено сообщение о запуске бота (только админу)")

    next_alive_interval = get_random_alive_interval()
    print(f"⏳ Следующее 'Бот жив' через {next_alive_interval // 60} минут")

    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка курса...")
            
            buy_rate, sell_rate = check_rate_once()

            if buy_rate is not None:
                update_count += 1
                
                is_profitable = check_conditions(buy_rate, sell_rate)

                if is_profitable:
                    if not was_profitable:
                        fast_check_counter = 0
                    fast_check_counter += 1
                else:
                    fast_check_counter = 0

                was_profitable = is_profitable

                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate if sell_rate else 0}")

                current_time = time.time()
                
                # --- "БОТ ЖИВ" — ТОЛЬКО АДМИНУ (каждые 5-10 минут) ---
                if current_time - last_alive_time >= next_alive_interval:
                    alive_count += 1
                    state = load_state()
                    state["alive_count"] = alive_count
                    save_state(state)
                    
                    alive_message = (
                        f"✅ Бот жив и работает!\n"
                        f"\n"
                        f"📊 Проверок: {update_count}\n"
                        f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                        f"🔴 Продажа: 100 => {sell_rate if sell_rate else '???'} оск.\n"
                        f"\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    send_vk_message_to_admin(alive_message)
                    last_alive_time = current_time
                    next_alive_interval = get_random_alive_interval()
                    print(f"💚 Отправлено 'Бот жив' админу (#{alive_count})")
                    print(f"⏳ Следующее через {next_alive_interval // 60} минут")

                # --- УВЕДОМЛЕНИЯ О ВЫГОДНОМ КУРСЕ — ВСЕМ ПОЛЬЗОВАТЕЛЯМ ---
                if buy_rate and sell_rate:
                    if is_profitable:
                        notification_count += 1
                        print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")

                        current_time = time.time()
                        if current_time - last_notification_time >= NOTIFICATION_INTERVAL:
                            message = (
                                f"🚨 ВЫГОДНЫЙ КУРС ОСКОЛКОВ! 🚨\n"
                                f"\n"
                                f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                                f"🔴 Продажа: 100 => {sell_rate} оск."
                            )

                            send_vk_message_to_all(message)
                            last_notification_time = current_time
                            print(f"📊 Следующее уведомление через {NOTIFICATION_INTERVAL} сек")
                        else:
                            wait_time = int(NOTIFICATION_INTERVAL - (current_time - last_notification_time))
                            print(f"⏳ Ожидаем {wait_time} сек перед следующим уведомлением")
                    else:
                        print(f"⏳ Условия не выполнены — сообщение НЕ отправлено")
                else:
                    print("⚠️ Не все данные получены")
            else:
                print("❌ Не удалось получить курс")

            # --- АДАПТИВНАЯ ЗАДЕРЖКА ---
            delay = get_check_delay(is_profitable, fast_check_counter)
            
            if is_profitable:
                if fast_check_counter <= FAST_CHECK_TIMES:
                    print(f"⚡ Быстрая проверка #{fast_check_counter}/{FAST_CHECK_TIMES} (интервал {delay} сек)")
                else:
                    print(f"📊 Обычная проверка выгодного курса (интервал {delay} сек)")
            else:
                print(f"🐢 Обычная проверка (интервал {delay} сек)")
            
            print(f"⏳ Следующая проверка через {delay} секунд...")
            time.sleep(delay)

        except KeyboardInterrupt:
            print("\n⏹ Остановка...")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            time.sleep(get_random_delay())


if __name__ == "__main__":
    main()
