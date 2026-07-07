import time
import re
import pickle
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
MAX_CHECK_INTERVAL = 7
NOTIFICATION_INTERVAL = 1

MIN_ALIVE_INTERVAL = 3600
MAX_ALIVE_INTERVAL = 7200

CLEANUP_INTERVAL = 900
CLEANUP_CHECK_COUNT = 100

DRIVER_RECREATE_INTERVAL = 1800
DRIVER_RECREATE_CHECK_COUNT = 200

STATE_FILE = "bot_state.pkl"

print("📌 Настройки загружены")

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
last_driver_recreate_time = time.time()
last_driver_recreate_check = 0

last_buy_rate = None
last_sell_rate = None
last_rate_time = 0
RATE_CACHE_TTL = 2


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
            return True
        except:
            return False
    
    with ThreadPoolExecutor(max_workers=len(USER_IDS)) as executor:
        results = list(executor.map(send_to_user, USER_IDS))
    
    success_count = sum(results)
    print(f"📊 Отправлено {success_count}/{len(USER_IDS)} сообщений")
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
    options.add_argument("--max_old_space_size=512")
    options.add_argument("--js-flags=--max-old-space-size=512")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-setuid-sandbox")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(3)
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        raise


def recreate_driver(driver):
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
    error = str(exception).lower()
    return "crashed" in error or "invalid session id" in error or "no such window" in error


def click_update_button(driver):
    """Нажатие кнопки 'Обновить курс'"""
    try:
        driver.execute_script("""
            var btns = document.querySelectorAll('*');
            for(var i=0; i<btns.length; i++) {
                if(btns[i].textContent && btns[i].textContent.includes('Обновить курс')) {
                    btns[i].click();
                    return true;
                }
            }
            return false;
        """)
        print("   ✅ Кнопка 'Обновить курс' нажата")
        time.sleep(0.5)
        return True
    except Exception as e:
        if is_driver_crashed(e):
            print(f"   💥 КРАШ: {e}")
            return "CRASH"
        
        try:
            buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Обновить курс')]")
            if buttons:
                buttons[0].click()
                print("   ✅ Кнопка 'Обновить курс' нажата (Selenium)")
                time.sleep(0.5)
                return True
        except:
            pass
        
        print("   ⚠️ Кнопка 'Обновить курс' не найдена")
        return False


def click_learn_button(driver):
    """Нажатие кнопки 'Узнать курс'"""
    try:
        driver.execute_script("""
            var btns = document.querySelectorAll('*');
            for(var i=0; i<btns.length; i++) {
                if(btns[i].textContent && btns[i].textContent.includes('Узнать курс')) {
                    btns[i].click();
                    return true;
                }
            }
            return false;
        """)
        print("   ✅ Кнопка 'Узнать курс' нажата")
        time.sleep(0.5)
        return True
    except Exception as e:
        if is_driver_crashed(e):
            print(f"   💥 КРАШ: {e}")
            return "CRASH"
        
        try:
            buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Узнать курс')]")
            if buttons:
                buttons[0].click()
                print("   ✅ Кнопка 'Узнать курс' нажата (Selenium)")
                time.sleep(0.5)
                return True
        except:
            pass
        
        print("   ⚠️ Кнопка 'Узнать курс' не найдена")
        return False


def get_rate_with_selenium(driver):
    """Получение курса: сначала Узнать курс, потом Обновить курс"""
    global last_buy_rate, last_sell_rate, last_rate_time
    
    current_time = time.time()
    if last_buy_rate and last_sell_rate and (current_time - last_rate_time) < RATE_CACHE_TTL:
        print("   ⚡ Кэш")
        return last_buy_rate, last_sell_rate
    
    try:
        # ПЕРЕХОДИМ НА СТРАНИЦУ
        driver.get(APP_URL)
        time.sleep(2)
        
        # ============================================
        # ШАГ 1: НАЖИМАЕМ "Узнать курс"
        # ============================================
        learn_result = click_learn_button(driver)
        if learn_result == "CRASH":
            return "CRASH", "CRASH"
        
        # ============================================
        # ШАГ 2: НАЖИМАЕМ "Обновить курс"
        # ============================================
        update_result = click_update_button(driver)
        if update_result == "CRASH":
            return "CRASH", "CRASH"
        
        # Ждем обновления
        time.sleep(1)
        
        # Получаем HTML
        html = driver.execute_script("return document.documentElement.outerHTML;")
        
        # 🔍 СОХРАНЯЕМ ДЛЯ ОТЛАДКИ
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Ищем курс
        buy_match = re.search(r'Покупка\s*[:]?\s*([0-9]+)', html, re.IGNORECASE)
        if not buy_match:
            buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
        if not buy_match:
            buy_match = re.search(r'Куплю[^0-9]*([0-9]+)', html)
        
        sell_match = re.search(r'Продажа\s*[:]?\s*[0-9]+\s*=>\s*([0-9]+)', html, re.IGNORECASE)
        if not sell_match:
            sell_match = re.search(r'Продажа[^0-9]*=>[^0-9]*([0-9]+)', html)
        if not sell_match:
            sell_match = re.search(r'Продажа[^0-9]*([0-9]+)', html)
        if not sell_match:
            sell_match = re.search(r'Продам[^0-9]*([0-9]+)', html)
        
        print(f"   🔍 buy_match: {buy_match.group(1) if buy_match else '❌'}")
        print(f"   🔍 sell_match: {sell_match.group(1) if sell_match else '❌'}")
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            
            last_buy_rate = buy_rate
            last_sell_rate = sell_rate
            last_rate_time = current_time
            
            print(f"   ✅ Курс: покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        # Если не нашли, выводим текст
        text = driver.find_element(By.TAG_NAME, "body").text
        print(f"   📄 Текст страницы: {text[:500]}")
        
        return None, None
    except Exception as e:
        if is_driver_crashed(e):
            print(f"   💥 КРАШ: {e}")
            return "CRASH", "CRASH"
        print(f"   ❌ Ошибка: {e}")
        return None, None


def clear_browser_data(driver):
    try:
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.delete_all_cookies()
    except:
        pass


def check_conditions(buy_rate, sell_rate):
    return buy_rate < BUY_THRESHOLD or sell_rate > SELL_THRESHOLD


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def get_random_alive_interval():
    return random.randint(MIN_ALIVE_INTERVAL, MAX_ALIVE_INTERVAL)


def main():
    global update_count, notification_count, last_alive_time, last_notification_time
    global last_cleanup_time, last_cleanup_check, last_driver_recreate_time, last_driver_recreate_check

    print("🤖 Бот для отслеживания курса осколков")
    print("=" * 60)
    print(f"📱 Админ: {ADMIN_ID}")
    print(f"📱 Получатели: {len(USER_IDS)}")
    print("=" * 60)
    print(f"🟢 Покупка < {BUY_THRESHOLD}")
    print(f"🔴 Продажа > {SELL_THRESHOLD}")
    print("=" * 60)
    print(f"⏰ Интервал: {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек")
    print("=" * 60)
    print("🔧 ПОРЯДОК ДЕЙСТВИЙ:")
    print("   1️⃣ Нажать 'Узнать курс'")
    print("   2️⃣ Нажать 'Обновить курс'")
    print("   3️⃣ Парсить курс")
    print("=" * 60)

    state = load_state()
    first_start_done = state.get("first_start_done", False)
    alive_count = state.get("alive_count", 0)

    if not first_start_done:
        start_message = (
            f"🚀 БОТ ЗАПУЩЕН!\n"
            f"🟢 Покупка < {BUY_THRESHOLD}\n"
            f"🔴 Продажа > {SELL_THRESHOLD}\n"
            f"⏰ {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек"
        )
        send_vk_message_to_admin(start_message)
        state["first_start_done"] = True
        save_state(state)

    next_alive_interval = get_random_alive_interval()

    print("\n🌐 Запуск браузера...")
    driver = get_driver()
    driver.get(APP_URL)
    time.sleep(2)

    print("\n🚀 Мониторинг запущен!")
    print("=" * 60)

    while True:
        try:
            start_time = time.time()
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка...")
            
            current_time = time.time()
            
            if (current_time - last_driver_recreate_time >= DRIVER_RECREATE_INTERVAL or 
                update_count - last_driver_recreate_check >= DRIVER_RECREATE_CHECK_COUNT):
                print("🔄 Плановое пересоздание...")
                driver = recreate_driver(driver)
                last_driver_recreate_time = current_time
                last_driver_recreate_check = update_count
                continue
            
            if (current_time - last_cleanup_time >= CLEANUP_INTERVAL or 
                update_count - last_cleanup_check >= CLEANUP_CHECK_COUNT):
                print("🔄 Очистка памяти...")
                clear_browser_data(driver)
                last_cleanup_time = current_time
                last_cleanup_check = update_count
            
            buy_rate, sell_rate = get_rate_with_selenium(driver)
            
            if buy_rate == "CRASH" and sell_rate == "CRASH":
                driver = recreate_driver(driver)
                continue

            if buy_rate is not None and sell_rate is not None:
                update_count += 1
                is_profitable = check_conditions(buy_rate, sell_rate)

                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

                if current_time - last_alive_time >= next_alive_interval:
                    alive_count += 1
                    state = load_state()
                    state["alive_count"] = alive_count
                    save_state(state)
                    
                    alive_message = (
                        f"✅ БОТ ЖИВ!\n"
                        f"📊 Проверок: {update_count}\n"
                        f"🟢 Покупка: {buy_rate}\n"
                        f"🔴 Продажа: {sell_rate}\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    send_vk_message_to_admin(alive_message)
                    last_alive_time = current_time
                    next_alive_interval = get_random_alive_interval()
                    print(f"💚 'Бот жив' #{alive_count}")

                if sell_rate > 0 and is_profitable:
                    notification_count += 1
                    print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! #{notification_count}")

                    if current_time - last_notification_time >= NOTIFICATION_INTERVAL:
                        message = (
                            f"🚨 ВЫГОДНЫЙ КУРС!\n"
                            f"🟢 Покупка: {buy_rate}\n"
                            f"🔴 Продажа: {sell_rate}\n"
                            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                        )
                        send_vk_message_to_all(message)
                        last_notification_time = current_time
                    else:
                        wait = int(NOTIFICATION_INTERVAL - (current_time - last_notification_time))
                        print(f"⏳ Ждем {wait} сек")
                else:
                    print(f"⏳ Условия не выполнены")
            else:
                print("❌ Не удалось получить курс")

            elapsed = time.time() - start_time
            delay = max(1, get_random_delay() - elapsed)
            
            print(f"⚡ За {elapsed:.2f} сек, следующая через {delay:.1f} сек")
            time.sleep(delay)

        except KeyboardInterrupt:
            print("\n⏹ Остановка...")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            
            if is_driver_crashed(e):
                print("💥 КРАШ! Пересоздаем...")
                driver = recreate_driver(driver)
            else:
                try:
                    driver = recreate_driver(driver)
                except:
                    driver = get_driver()
                    driver.get(APP_URL)
                    time.sleep(1)
            time.sleep(get_random_delay())
    
    try:
        driver.quit()
        print("✅ Браузер закрыт")
    except:
        pass


if __name__ == "__main__":
    main()
