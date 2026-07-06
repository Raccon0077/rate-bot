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
SELL_THRESHOLD = 60000

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

# --- ИНТЕРВАЛЫ ---
MIN_CHECK_INTERVAL = 4   # 4 секунды минимум
MAX_CHECK_INTERVAL = 7   # 7 секунд максимум
NOTIFICATION_INTERVAL = 1

# --- "БОТ ЖИВ" - 1-2 ЧАСА ---
MIN_ALIVE_INTERVAL = 3600   # 1 час
MAX_ALIVE_INTERVAL = 7200   # 2 часа

# --- ОЧИСТКА ПАМЯТИ ---
CLEANUP_INTERVAL = 900  # 15 минут
CLEANUP_CHECK_COUNT = 100  # Каждые 100 проверок

# --- ПЕРЕСОЗДАНИЕ ДРАЙВЕРА ---
DRIVER_RECREATE_INTERVAL = 3600  # 60 минут
DRIVER_RECREATE_CHECK_COUNT = 200

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
last_driver_recreate_time = time.time()
last_driver_recreate_check = 0

# Кэш для хранения последнего курса
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
    """Создает оптимизированный драйвер"""
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
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(3)
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        raise


def click_update_button(driver):
    """БЫСТРЫЙ клик по кнопке 'Обновить курс' через JavaScript"""
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
        print("   ✅ Кнопка 'Обновить курс' нажата (JS)")
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"   ⚠️ Ошибка клика через JS: {e}")
        
        try:
            buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Обновить курс')]")
            if buttons:
                buttons[0].click()
                print("   ✅ Кнопка 'Обновить курс' нажата (Selenium)")
                time.sleep(0.3)
                return True
        except:
            pass
        
        print("   ⚠️ Кнопка 'Обновить курс' не найдена")
        return False


def get_rate_selenium(driver):
    """Получение курса через Selenium с кэшированием"""
    global last_buy_rate, last_sell_rate, last_rate_time
    
    # Проверяем кэш
    current_time = time.time()
    if last_buy_rate and last_sell_rate and (current_time - last_rate_time) < RATE_CACHE_TTL:
        print("   ⚡ Используем кэшированный курс")
        return last_buy_rate, last_sell_rate
    
    try:
        # Кликаем кнопку
        click_update_button(driver)
        
        # Получаем HTML через Selenium
        html = driver.page_source
        
        # Парсим курс
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
        sell_match = re.search(r'Продажа[^0-9]*💎100[^0-9]*=>?[^0-9]*🌕([0-9]+)', html)
        
        if not sell_match:
            sell_match = re.search(r'Продажа[^0-9]*=>[^0-9]*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            
            # Обновляем кэш
            last_buy_rate = buy_rate
            last_sell_rate = sell_rate
            last_rate_time = current_time
            
            return buy_rate, sell_rate
        
        return None, None
    except Exception as e:
        print(f"   ❌ Ошибка получения курса: {e}")
        return None, None


def update_page_fast(driver):
    """БЫСТРОЕ обновление страницы"""
    try:
        driver.execute_script("location.reload();")
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"   ⚠️ Ошибка обновления: {e}")
        return False


def clear_browser_data(driver):
    try:
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.delete_all_cookies()
    except:
        pass


def recreate_driver(driver):
    try:
        driver.quit()
    except:
        pass
    time.sleep(1)
    new_driver = get_driver()
    new_driver.get(APP_URL)
    time.sleep(1)
    return new_driver


def check_conditions(buy_rate, sell_rate):
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    return buy_condition or sell_condition


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def get_random_alive_interval():
    return random.randint(MIN_ALIVE_INTERVAL, MAX_ALIVE_INTERVAL)


def main():
    global update_count, notification_count, last_alive_time, last_notification_time
    global last_cleanup_time, last_cleanup_check, last_driver_recreate_time, last_driver_recreate_check

    print("🤖 Бот для отслеживания курса осколков (Selenium)")
    print("=" * 60)
    print(f"📱 Админ: {ADMIN_ID}")
    print(f"📱 Получатели: {len(USER_IDS)}")
    print("=" * 60)
    print("📊 УСЛОВИЯ (ИЛИ):")
    print(f"   1️⃣ Покупка < {BUY_THRESHOLD}")
    print(f"   2️⃣ Продажа > {SELL_THRESHOLD}")
    print("=" * 60)
    print("⚡ НАСТРОЙКИ:")
    print(f"   - JavaScript для кликов")
    print(f"   - Кэширование курса: {RATE_CACHE_TTL} сек")
    print(f"   - Параллельная отправка сообщений")
    print("=" * 60)
    print(f"⏰ Интервал проверки: {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек")
    print(f"⏰ 'Бот жив': {MIN_ALIVE_INTERVAL//3600}-{MAX_ALIVE_INTERVAL//3600} часов")
    print("=" * 60)

    state = load_state()
    first_start_done = state.get("first_start_done", False)
    alive_count = state.get("alive_count", 0)

    if not first_start_done:
        start_message = (
            f"🚀 БОТ ЗАПУЩЕН! (SELENIUM)\n"
            f"\n"
            f"⚡ JavaScript для быстрых кликов\n"
            f"📊 Отслеживание курса осколков\n"
            f"🟢 Покупка: ниже {BUY_THRESHOLD}\n"
            f"🔴 Продажа: выше {SELL_THRESHOLD}\n"
            f"⏰ Проверка: {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек"
        )
        send_vk_message_to_admin(start_message)
        state["first_start_done"] = True
        save_state(state)

    next_alive_interval = get_random_alive_interval()
    print(f"⏳ Следующее 'Бот жив' через {next_alive_interval // 60} минут")

    print("\n🌐 Запускаем браузер...")
    driver = get_driver()
    driver.get(APP_URL)
    time.sleep(1)

    print("\n🚀 Запускаем мониторинг...")
    print("=" * 60)

    while True:
        try:
            start_time = time.time()
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Проверка курса...")
            
            current_time = time.time()
            
            # --- ПРОВЕРКА ПЕРЕСОЗДАНИЯ ДРАЙВЕРА ---
            if (current_time - last_driver_recreate_time >= DRIVER_RECREATE_INTERVAL or 
                update_count - last_driver_recreate_check >= DRIVER_RECREATE_CHECK_COUNT):
                print("🔄 Пересоздание драйвера...")
                driver = recreate_driver(driver)
                last_driver_recreate_time = current_time
                last_driver_recreate_check = update_count
                continue
            
            # --- ПРОВЕРКА ОЧИСТКИ ---
            if (current_time - last_cleanup_time >= CLEANUP_INTERVAL or 
                update_count - last_cleanup_check >= CLEANUP_CHECK_COUNT):
                print("🔄 Очистка памяти...")
                clear_browser_data(driver)
                last_cleanup_time = current_time
                last_cleanup_check = update_count
            
            # --- ПОЛУЧЕНИЕ КУРСА ---
            buy_rate, sell_rate = get_rate_selenium(driver)

            if buy_rate is not None:
                update_count += 1
                
                is_profitable = check_conditions(buy_rate, sell_rate)

                print(f"📊 #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

                # --- "БОТ ЖИВ" (1-2 часа) ---
                if current_time - last_alive_time >= next_alive_interval:
                    alive_count += 1
                    state = load_state()
                    state["alive_count"] = alive_count
                    save_state(state)
                    
                    alive_message = (
                        f"✅ БОТ ЖИВ!\n"
                        f"\n"
                        f"📊 Проверок: {update_count}\n"
                        f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                        f"🔴 Продажа: 100 => {sell_rate} оск.\n"
                        f"🔄 Уведомление #{alive_count}\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    send_vk_message_to_admin(alive_message)
                    last_alive_time = current_time
                    next_alive_interval = get_random_alive_interval()
                    print(f"💚 Отправлено 'Бот жив' админу (#{alive_count})")
                    print(f"⏳ Следующее через {next_alive_interval // 60} минут")

                # --- УВЕДОМЛЕНИЯ ---
                if sell_rate > 0 and is_profitable:
                    notification_count += 1
                    print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")

                    if current_time - last_notification_time >= NOTIFICATION_INTERVAL:
                        message = (
                            f"🚨 ВЫГОДНЫЙ КУРС ОСКОЛКОВ! 🚨\n"
                            f"\n"
                            f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                            f"🔴 Продажа: 100 => {sell_rate} оск.\n"
                            f"\n"
                            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                        )
                        send_vk_message_to_all(message)
                        last_notification_time = current_time
                    else:
                        wait_time = int(NOTIFICATION_INTERVAL - (current_time - last_notification_time))
                        print(f"⏳ Ожидаем {wait_time} сек")
                else:
                    if sell_rate > 0:
                        print(f"⏳ Условия не выполнены")
                    else:
                        print(f"⚠️ Данные неполные")
            else:
                print("❌ Не удалось получить курс")

            # --- РАСЧЕТ ЗАДЕРЖКИ (4-7 секунд) ---
            elapsed = time.time() - start_time
            delay = max(1, get_random_delay() - elapsed)
            
            print(f"⚡ Проверка выполнена за {elapsed:.2f} сек")
            print(f"⏳ Следующая проверка через {delay:.1f} сек...")
            time.sleep(delay)

        except KeyboardInterrupt:
            print("\n⏹ Остановка...")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            try:
                print("🔄 Восстановление драйвера...")
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
