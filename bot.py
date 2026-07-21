import time
import re
import pickle
import os
import random
import requests
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
MIN_CHECK_INTERVAL = 5        # Увеличил до 5 секунд для стабильности
MAX_CHECK_INTERVAL = 8        # Увеличил до 8 секунд
NOTIFICATION_INTERVAL = 0.5
MIN_ALIVE_INTERVAL = 300
MAX_ALIVE_INTERVAL = 1800

STATE_FILE = "bot_state.pkl"
LAST_NOTIFICATION_FILE = "last_notification.pkl"

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

# --- ФУНКЦИИ ДЛЯ ОТСЛЕЖИВАНИЯ ЛУЧШЕГО КУРСА ---
def load_last_notification():
    try:
        if os.path.exists(LAST_NOTIFICATION_FILE):
            with open(LAST_NOTIFICATION_FILE, "rb") as f:
                return pickle.load(f)
        return {"buy_rate": None, "sell_rate": None, "best_buy": None, "best_sell": None}
    except:
        return {"buy_rate": None, "sell_rate": None, "best_buy": None, "best_sell": None}

def save_last_notification(buy_rate, sell_rate, best_buy, best_sell):
    try:
        with open(LAST_NOTIFICATION_FILE, "wb") as f:
            pickle.dump({
                "buy_rate": buy_rate,
                "sell_rate": sell_rate,
                "best_buy": best_buy if best_buy is not None else buy_rate,
                "best_sell": best_sell if best_sell is not None else sell_rate
            }, f)
    except:
        pass

def should_send_notification(buy_rate, sell_rate):
    last = load_last_notification()
    
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    
    if not buy_condition and not sell_condition:
        return False, None, None, None
    
    best_buy = last.get("best_buy")
    best_sell = last.get("best_sell")
    
    if best_buy is None and best_sell is None:
        return True, buy_rate, sell_rate, buy_rate, sell_rate
    
    should_send = False
    new_best_buy = best_buy
    new_best_sell = best_sell
    
    if buy_condition:
        if best_buy is None or buy_rate < best_buy:
            should_send = True
            new_best_buy = buy_rate
            print(f"   📉 НОВЫЙ МИНИМУМ покупки: {buy_rate} (было {best_buy})")
    
    if sell_condition:
        if best_sell is None or sell_rate > best_sell:
            should_send = True
            new_best_sell = sell_rate
            print(f"   📈 НОВЫЙ МАКСИМУМ продажи: {sell_rate} (было {best_sell})")
    
    if should_send:
        return True, buy_rate, sell_rate, new_best_buy, new_best_sell
    
    print(f"   ⏳ Курс не улучшился: покупка {buy_rate} (лучший {best_buy}), продажа {sell_rate} (лучший {best_sell})")
    return False, None, None, None, None

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

# --- ОПТИМИЗИРОВАННЫЙ ДРАЙВЕР ---
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
    
    # Дополнительные опции для стабильности
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    
    # Ускоряем загрузку
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(5)
        driver.implicitly_wait(1)
        print("✅ Драйвер создан (оптимизированный)")
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        raise

def recreate_driver(driver):
    """Пересоздание драйвера при краше (улучшенное)"""
    print("   🔄 ПЕРЕСОЗДАНИЕ ДРАЙВЕРА...")
    
    # Закрываем старый драйвер
    try:
        driver.quit()
    except:
        pass
    
    # Принудительно закрываем все процессы Chrome (для Windows)
    try:
        os.system("taskkill /f /im chrome.exe 2>nul")
        os.system("taskkill /f /im chromedriver.exe 2>nul")
    except:
        pass
    
    time.sleep(3)  # Увеличил до 3 секунд
    
    # Создаем новый драйвер
    new_driver = get_driver()
    try:
        new_driver.get(APP_URL)
        time.sleep(2)
        print("   ✅ Драйвер пересоздан")
        return new_driver
    except Exception as e:
        print(f"   ❌ Ошибка при загрузке страницы: {e}")
        time.sleep(2)
        # Пробуем еще раз
        try:
            new_driver.get(APP_URL)
            time.sleep(2)
            return new_driver
        except:
            print("   ❌ КРИТИЧЕСКАЯ ОШИБКА! Возвращаем новый драйвер")
            return new_driver

def is_driver_crashed(exception):
    error = str(exception).lower()
    return ("crashed" in error or 
            "invalid session" in error or 
            "no such window" in error or 
            "tab crashed" in error or
            "disconnected" in error or
            "cannot connect" in error)

# --- БЫСТРЫЙ ПАРСИНГ ---
def parse_rate_from_html(html):
    buy_rate = None
    sell_rate = None
    
    buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
    if buy_match:
        buy_rate = int(buy_match.group(1))
    
    sell_match = re.search(r'Продажа[^0-9]*=>?[^0-9]*([0-9]+)', html)
    if sell_match:
        sell_rate = int(sell_match.group(1))
    
    if buy_rate and sell_rate:
        return buy_rate, sell_rate
    if buy_rate:
        return buy_rate, 0
    return None, None

def check_conditions(buy_rate, sell_rate):
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    result = buy_condition or sell_condition
    print(f"   📋 Условия: покупка {buy_rate} < {BUY_THRESHOLD} = {buy_condition}, продажа {sell_rate} > {SELL_THRESHOLD} = {sell_condition}, результат: {result}")
    return result

def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)

def get_random_alive_interval():
    return random.randint(MIN_ALIVE_INTERVAL, MAX_ALIVE_INTERVAL)

# --- БЫСТРОЕ ПОЛУЧЕНИЕ КУРСА ---
def get_rate_fast(driver):
    """
    МАКСИМАЛЬНО БЫСТРОЕ ПОЛУЧЕНИЕ КУРСА
    """
    start_time = time.time()
    
    try:
        # ПРОВЕРКА: жив ли драйвер
        try:
            driver.current_url
        except Exception as e:
            if is_driver_crashed(e):
                print("💥 ДРАЙВЕР МЕРТВ!")
                return None, None
        
        # 1. Обновляем страницу
        driver.refresh()
        time.sleep(0.2)
        
        # 2. Нажимаем "Узнать курс"
        try:
            learn_btn = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Узнать курс')]"))
            )
            learn_btn.click()
            time.sleep(0.1)
        except Exception as e:
            if is_driver_crashed(e):
                print("💥 КРАШ при клике 'Узнать курс'")
                return None, None
            print(f"   ⚠️ Кнопка 'Узнать курс' не найдена")
        
        # 3. Нажимаем "Обновить курс"
        try:
            update_btn = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Обновить курс')]"))
            )
            update_btn.click()
            time.sleep(0.15)
        except Exception as e:
            if is_driver_crashed(e):
                print("💥 КРАШ при клике 'Обновить курс'")
                return None, None
            print(f"   ⚠️ Кнопка 'Обновить курс' не найдена")
        
        # 4. Получаем HTML
        try:
            html = driver.page_source
        except Exception as e:
            if is_driver_crashed(e):
                print("💥 КРАШ при получении HTML")
                return None, None
            raise
        
        # 5. Парсим
        buy_rate, sell_rate = parse_rate_from_html(html)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Проверка заняла {elapsed:.2f} сек")
        
        return buy_rate, sell_rate
        
    except Exception as e:
        print(f"❌ Ошибка получения курса: {e}")
        if is_driver_crashed(e):
            return None, None
        return None, None

# --- ПОЛУЧЕНИЕ КУРСА С АВТОВОССТАНОВЛЕНИЕМ ---
def get_rate_with_recovery(driver):
    """
    Получение курса с автоматическим восстановлением при краше
    """
    max_retries = 3
    retry_count = 0
    current_driver = driver
    
    while retry_count < max_retries:
        try:
            buy_rate, sell_rate = get_rate_fast(current_driver)
            
            if buy_rate is not None:
                return buy_rate, sell_rate, current_driver
            else:
                # Если вернулись None, значит краш
                retry_count += 1
                print(f"💥 КРАШ! Попытка {retry_count}/{max_retries}...")
                current_driver = recreate_driver(current_driver)
                continue
                
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Исключение: {e}")
            
            if is_driver_crashed(e):
                retry_count += 1
                print(f"💥 КРАШ БРАУЗЕРА! Попытка {retry_count}/{max_retries}...")
                current_driver = recreate_driver(current_driver)
                
                if retry_count >= max_retries:
                    print("❌ Все попытки восстановления не удались")
                    return None, None, current_driver
                
                time.sleep(1)
            else:
                # Другая ошибка
                print(f"❌ Ошибка получения курса: {e}")
                return None, None, current_driver
    
    return None, None, current_driver

def main():
    global update_count, notification_count, last_alive_time, last_notification_time

    print("🤖 Бот для отслеживания курса осколков (МАКСИМАЛЬНО БЫСТРЫЙ + АВТОВОССТАНОВЛЕНИЕ)")
    print("=" * 60)
    print(f"📱 Админ: {ADMIN_ID}")
    print(f"📱 Получатели: {USER_IDS}")
    print("=" * 60)
    print("📊 УСЛОВИЯ (ИЛИ):")
    print(f"   1️⃣ Покупка < {BUY_THRESHOLD}")
    print(f"   2️⃣ Продажа > {SELL_THRESHOLD}")
    print("=" * 60)
    print("⚡ СКОРОСТЬ:")
    print(f"   - Проверка курса: {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек")
    print(f"   - Время одной проверки: ~1-2 секунды")
    print("=" * 60)
    print("🔄 АВТОВОССТАНОВЛЕНИЕ:")
    print("   - При краше браузера автоматическое пересоздание")
    print("   - До 3 попыток восстановления")
    print("=" * 60)

    state = load_state()
    first_start_done = state.get("first_start_done", False)
    alive_count = state.get("alive_count", 0)

    if not first_start_done:
        start_message = (
            f"🚀 БОТ ЗАПУЩЕН!\n"
            f"\n"
            f"📊 Отслеживание курса осколков\n"
            f"🟢 Покупка: ниже {BUY_THRESHOLD}\n"
            f"🔴 Продажа: выше {SELL_THRESHOLD}\n"
            f"⚡ Проверка каждые {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек\n"
            f"🔄 Автовосстановление при краше\n"
            f"📢 Уведомления только при улучшении курса"
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
            
            # --- ПОЛУЧАЕМ КУРС С АВТОВОССТАНОВЛЕНИЕМ ---
            buy_rate, sell_rate, driver = get_rate_with_recovery(driver)
            
            if buy_rate is None:
                print("❌ Не удалось получить курс, пробуем снова...")
                time.sleep(3)
                continue

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
                    f"⚡ Интервал: {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} сек\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
                send_vk_message_to_admin(alive_message)
                last_alive_time = current_time
                next_alive_interval = get_random_alive_interval()
                print(f"💚 Отправлено 'Бот жив' админу (#{alive_count})")
                print(f"⏳ Следующее через {next_alive_interval // 60} минут")

            # --- УВЕДОМЛЕНИЯ ТОЛЬКО ПРИ УЛУЧШЕНИИ ---
            if buy_rate and sell_rate:
                if is_profitable:
                    should_send, _, _, new_best_buy, new_best_sell = should_send_notification(buy_rate, sell_rate)
                    
                    if should_send:
                        notification_count += 1
                        print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")

                        current_time = time.time()
                        if current_time - last_notification_time >= NOTIFICATION_INTERVAL:
                            buy_condition = buy_rate < BUY_THRESHOLD
                            sell_condition = sell_rate > SELL_THRESHOLD
                            
                            if buy_condition and sell_condition:
                                message = (
                                    f"🚨 ВЫГОДНЫЙ КУРС ОСКОЛКОВ! 🚨\n"
                                    f"\n"
                                    f"🟢 Покупка: {buy_rate} => 100 оск.\n"
                                    f"🔴 Продажа: 100 => {sell_rate} оск.\n"
                                    f"\n"
                                    f"🏆 Лучший курс за сессию:\n"
                                    f"   Покупка: {new_best_buy if new_best_buy else buy_rate}\n"
                                    f"   Продажа: {new_best_sell if new_best_sell else sell_rate}"
                                )
                            elif buy_condition:
                                message = (
                                    f"🟢 ВЫГОДНАЯ ПОКУПКА ОСКОЛКОВ!\n"
                                    f"\n"
                                    f"💎 {buy_rate} => 100 оск.\n"
                                    f"📉 Курс упал до {buy_rate} (ниже {BUY_THRESHOLD})\n"
                                    f"\n"
                                    f"🏆 Лучший курс: {new_best_buy if new_best_buy else buy_rate}"
                                )
                            else:
                                message = (
                                    f"🔴 ВЫГОДНАЯ ПРОДАЖА ОСКОЛКОВ!\n"
                                    f"\n"
                                    f"🌕 100 => {sell_rate} оск.\n"
                                    f"📈 Курс вырос до {sell_rate} (выше {SELL_THRESHOLD})\n"
                                    f"\n"
                                    f"🏆 Лучший курс: {new_best_sell if new_best_sell else sell_rate}"
                                )

                            send_vk_message_to_all(message)
                            last_notification_time = current_time
                            save_last_notification(buy_rate, sell_rate, new_best_buy, new_best_sell)
                            print(f"📊 Следующее уведомление через {NOTIFICATION_INTERVAL} сек")
                        else:
                            wait_time = int(NOTIFICATION_INTERVAL - (current_time - last_notification_time))
                            print(f"⏳ Ожидаем {wait_time} сек перед следующим уведомлением")
                    else:
                        print(f"⏳ Курс не улучшился - сообщение НЕ отправлено")
                else:
                    print(f"⏳ Условия не выполнены — сообщение НЕ отправлено")
            else:
                print("⚠️ Не все данные получены")

            delay = get_random_delay()
            print(f"⚡ Следующая проверка через {delay} секунд...")
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
