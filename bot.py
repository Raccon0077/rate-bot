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
from concurrent.futures import ThreadPoolExecutor

print("🚀 Бот запускается...")

# --- НАСТРОЙКИ ---
GROUP_TOKEN = "vk1.a.AmFPbkY4T9acuaWmLC1gQYNU3DqhZpS1PR1CMlSR7GV36ryU7ogRz2URrgnXYGZYYm_h0SQBhy71_5AG5HcIb3csegaBnks_1PweRiC20t5Im-hfbhkZnVNykMmFJBEbzPZ52WoJWzXPPZYXwa1_wJfxmtfmd86W7OcBSMuK2AGCYsJO97g6MB5pPhLRYJVE_KFBO9lK0JpfeiPPy9aRSg"

ADMIN_ID = 212887447
USER_IDS = [
    212887447,
    145156004,
    816395698,
    459341710,
]

BUY_THRESHOLD = 50000
SELL_THRESHOLD = 70000

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

# --- ИНТЕРВАЛЫ ---
MIN_CHECK_INTERVAL = 4
MAX_CHECK_INTERVAL = 8
NOTIFICATION_INTERVAL = 0.5
MIN_ALIVE_INTERVAL = 300
MAX_ALIVE_INTERVAL = 1800

# --- ОЧИСТКА ПАМЯТИ ---
CLEANUP_INTERVAL = 600
CLEANUP_CHECK_COUNT = 50

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
last_cleanup_time = time.time()
last_cleanup_check = 0


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
    def send_to_user(user_id):
        try:
            vk.messages.send(
                user_id=user_id,
                random_id=get_random_id(),
                message=text
            )
            print(f"   ✅ Отправлено пользователю {user_id}")
            return True
        except Exception as e:
            print(f"   ❌ Ошибка отправки пользователю {user_id}: {e}")
            return False
    
    with ThreadPoolExecutor(max_workers=len(USER_IDS)) as executor:
        results = list(executor.map(send_to_user, USER_IDS))
    
    success_count = sum(results)
    fail_count = len(USER_IDS) - success_count
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
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-setuid-sandbox")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(3)
        print("✅ Драйвер создан")
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        raise


def recreate_driver(driver):
    """Пересоздание драйвера при краше"""
    print("   🔄 ПЕРЕСОЗДАНИЕ ДРАЙВЕРА...")
    try:
        driver.quit()
    except:
        pass
    time.sleep(2)
    new_driver = get_driver()
    new_driver.get(APP_URL)
    time.sleep(1)
    print("   ✅ Драйвер пересоздан")
    return new_driver


def is_driver_crashed(exception):
    """Проверяет, крашнулся ли браузер"""
    error = str(exception).lower()
    return "crashed" in error or "invalid session id" in error or "no such window" in error or "tab crashed" in error


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


def deep_cleanup(driver):
    try:
        driver.execute_script("window.location.reload(true);")
        print("🔄 Страница перезагружена с очисткой кэша")
        time.sleep(1)
    except:
        pass
    clear_browser_data(driver)
    return driver


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
    return random.randint(MIN_ALIVE_INTERVAL, MAX_ALIVE_INTERVAL)


def main():
    global update_count, notification_count, last_alive_time, last_notification_time, last_cleanup_time, last_cleanup_check

    print("🤖 Бот для отслеживания курса осколков (С АВТОВОССТАНОВЛЕНИЕМ)")
    print("=" * 60)
    print(f"📱 Админ: {ADMIN_ID}")
    print(f"📱 Получатели: {USER_IDS}")
    print("=" * 60)
    print("📊 УСЛОВИЯ (ИЛИ):")
    print(f"   1️⃣ Покупка < {BUY_THRESHOLD}")
    print(f"   2️⃣ Продажа > {SELL_THRESHOLD}")
    print("=" * 60)
    print("📢 ИНТЕРВАЛЫ:")
    print(f"   - Проверка курса: {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек")
    print(f"   - 'Бот жив': {MIN_ALIVE_INTERVAL//60}-{MAX_ALIVE_INTERVAL//60} минут")
    print("=" * 60)
    print("🔄 АВТОВОССТАНОВЛЕНИЕ:")
    print("   - При краше браузера драйвер пересоздается автоматически")
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
            f"🔴 Продажа: выше {SELL_THRESHOLD}\n"
            f"🔄 Автовосстановление при краше браузера"
        )
        send_vk_message_to_admin(start_message)
        state["first_start_done"] = True
        save_state(state)
        print("💚 Отправлено сообщение о запуске бота (только админу)")

    next_alive_interval = get_random_alive_interval()
    print(f"⏳ Следующее 'Бот жив' через {next_alive_interval // 60} минут")

    print("\n🌐 Запускаем браузер...")
    driver = get_driver()
    driver.get(APP_URL)
    time.sleep(2)

    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка курса...")
            
            # --- ПРОВЕРКА ОЧИСТКИ ПАМЯТИ ---
            current_time = time.time()
            need_cleanup = False
            reason = ""
            
            if current_time - last_cleanup_time >= CLEANUP_INTERVAL:
                need_cleanup = True
                reason = f"прошло {CLEANUP_INTERVAL//60} минут"
            
            if update_count - last_cleanup_check >= CLEANUP_CHECK_COUNT:
                need_cleanup = True
                reason = f"выполнено {CLEANUP_CHECK_COUNT} проверок"
            
            if need_cleanup:
                print(f"🔄 Очистка памяти ({reason})...")
                
                cleanup_message = (
                    f"💾 ОЧИСТКА ПАМЯТИ (без перезапуска)!\n"
                    f"\n"
                    f"📊 Причина: {reason}\n"
                    f"📊 Проверок: {update_count}\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
                send_vk_message_to_admin(cleanup_message)
                
                driver = deep_cleanup(driver)
                last_cleanup_time = current_time
                last_cleanup_check = update_count
                print("✅ Память очищена")
            else:
                clear_browser_data(driver)
            
            # --- ОБНОВЛЯЕМ СТРАНИЦУ ---
            try:
                print("🔄 Обновляем страницу...")
                driver.refresh()
                time.sleep(0.3)
            except Exception as e:
                if is_driver_crashed(e):
                    print(f"💥 КРАШ при обновлении, пересоздаем драйвер...")
                    driver = recreate_driver(driver)
                    continue
                else:
                    raise
            
            # --- НАЖИМАЕМ "Узнать курс" ---
            try:
                print("🔄 Нажимаем 'Узнать курс'...")
                learn_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Узнать курс')]"))
                )
                learn_btn.click()
                print("   ✅ Нажата кнопка 'Узнать курс'")
                time.sleep(0.2)
            except Exception as e:
                if is_driver_crashed(e):
                    print(f"💥 КРАШ при клике 'Узнать курс', пересоздаем драйвер...")
                    driver = recreate_driver(driver)
                    continue
                print(f"   ⚠️ Кнопка 'Узнать курс' не найдена: {e}")
            
            # --- НАЖИМАЕМ "Обновить курс" ---
            try:
                print("🔄 Нажимаем 'Обновить курс'...")
                update_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Обновить курс')]"))
                )
                update_btn.click()
                print("   ✅ Нажата кнопка 'Обновить курс'")
                time.sleep(0.2)
            except Exception as e:
                if is_driver_crashed(e):
                    print(f"💥 КРАШ при клике 'Обновить курс', пересоздаем драйвер...")
                    driver = recreate_driver(driver)
                    continue
                print(f"   ⚠️ Кнопка 'Обновить курс' не найдена: {e}")
            
            # --- ПОЛУЧАЕМ HTML ---
            try:
                html = driver.page_source
                print(f"📄 HTML получен, длина: {len(html)}")
            except Exception as e:
                if is_driver_crashed(e):
                    print(f"💥 КРАШ при получении HTML, пересоздаем драйвер...")
                    driver = recreate_driver(driver)
                    continue
                else:
                    raise
            
            # --- ПАРСИМ КУРС ---
            buy_rate, sell_rate = parse_rate_from_html(html)

            if buy_rate is not None:
                update_count += 1
                
                is_profitable = check_conditions(buy_rate, sell_rate)

                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate if sell_rate else 0}")

                current_time = time.time()
                
                # --- "БОТ ЖИВ" ---
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
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    send_vk_message_to_admin(alive_message)
                    last_alive_time = current_time
                    next_alive_interval = get_random_alive_interval()
                    print(f"💚 Отправлено 'Бот жив' админу (#{alive_count})")
                    print(f"⏳ Следующее через {next_alive_interval // 60} минут")

                # --- УВЕДОМЛЕНИЯ ---
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

            delay = get_random_delay()
            print(f"🐢 Обычная проверка (интервал {delay} сек)")
            print(f"⏳ Следующая проверка через {delay} секунд...")
            time.sleep(delay)

        except KeyboardInterrupt:
            print("\n⏹ Остановка...")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            
            if is_driver_crashed(e):
                print("💥 КРАШ БРАУЗЕРА! Пересоздаем драйвер...")
                driver = recreate_driver(driver)
            else:
                try:
                    driver.get(APP_URL)
                    time.sleep(2)
                except:
                    driver = recreate_driver(driver)
            time.sleep(get_random_delay())
    
    try:
        driver.quit()
        print("✅ Браузер закрыт")
    except:
        pass


if __name__ == "__main__":
    main()
