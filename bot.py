import time
import re
import pickle
import os
import shutil
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

# --- НАСТРОЙКИ ---
GROUP_TOKEN = "vk1.a.8Gc4tpdnYrLN_BRQ1puFlBBWac3X6AivdJGP2S5pNsVIspW2kfn4dWV6nmFh_X8TWKkZm9yzST751CQFdJ84-J30Uq_T_sFoRshtOlgLDlUZ97VAzgDcoj1jh5s5j6ExbTEcNAmNqhgGo6MpjPf8WIPNbyULTIazIJhyLThAHLx8EyLAjyh9Ya8wNrYRK_jyiTqckSnoDHPutcJOk8khpg"

# --- СПИСОК ПОЛУЧАТЕЛЕЙ ---
USER_IDS = [
    212887447,
    145156004,
]

# --- УСЛОВИЯ ---
BUY_THRESHOLD = 50000
SELL_THRESHOLD = 60000

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

MIN_CHECK_INTERVAL = 5
MAX_CHECK_INTERVAL = 13

SAVED_URL_FILE = "saved_url.pkl"
TEMP_PROFILE_DIR = "chromedriver_profile"

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


def delete_temp_profile():
    try:
        if os.path.exists(TEMP_PROFILE_DIR):
            shutil.rmtree(TEMP_PROFILE_DIR)
            print(f"🗑️ Старый профиль удалён: {TEMP_PROFILE_DIR}")
        else:
            print("ℹ️ Профиль не найден, создаём новый")
    except Exception as e:
        print(f"⚠️ Ошибка удаления профиля: {e}")


def save_url(url, filename=SAVED_URL_FILE):
    try:
        with open(filename, "wb") as f:
            pickle.dump(url, f)
        print(f"✅ URL сохранён: {url}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения URL: {e}")
        return False


def load_url(filename=SAVED_URL_FILE):
    try:
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                url = pickle.load(f)
            print(f"✅ Загружен сохранённый URL: {url}")
            return url
        else:
            print("⚠️ Сохранённый URL не найден")
            return None
    except Exception as e:
        print(f"❌ Ошибка загрузки URL: {e}")
        return None


def click_update_button(driver):
    try:
        buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Обновить курс')]")
        if buttons:
            buttons[0].click()
            print("🔄 Кнопка 'Обновить курс' нажата")
            time.sleep(1.5)
            return True
        else:
            buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Обновить')]")
            for btn in buttons:
                if 'курс' in btn.text.lower():
                    btn.click()
                    print("🔄 Кнопка 'Обновить курс' нажата")
                    time.sleep(1.5)
                    return True
            print("⚠️ Кнопка 'Обновить курс' не найдена")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка при нажатии кнопки: {e}")
        return False


def parse_rate(driver):
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split('\n')
        buy_rate = None
        sell_rate = None

        for line in lines:
            if 'Покупка' in line:
                match = re.search(r'Покупка[^0-9]*([0-9]+)\s*=>', line)
                if match:
                    buy_rate = int(match.group(1))
            if 'Продажа' in line:
                match = re.search(r'=>\s*[^0-9]*([0-9]+)', line)
                if match:
                    sell_rate = int(match.group(1))

        if buy_rate and sell_rate:
            return buy_rate, sell_rate
        return None, None
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        return None, None


def check_conditions(buy_rate, sell_rate):
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    return buy_condition or sell_condition


def get_condition_text(buy_rate, sell_rate):
    conditions = []
    if buy_rate < BUY_THRESHOLD:
        conditions.append(f"✅ Покупка {buy_rate} < {BUY_THRESHOLD}")
    else:
        conditions.append(f"❌ Покупка {buy_rate} >= {BUY_THRESHOLD}")
    if sell_rate > SELL_THRESHOLD:
        conditions.append(f"✅ Продажа {sell_rate} > {SELL_THRESHOLD}")
    else:
        conditions.append(f"❌ Продажа {sell_rate} <= {SELL_THRESHOLD}")
    return "\n".join(conditions)


def get_notification_interval(notification_count):
    if notification_count < 2:
        return 5
    else:
        return 10


def get_random_delay():
    return random.randint(MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL)


def get_driver():
    """Создаёт и возвращает драйвер Chrome с headless-настройками"""
    options = Options()

    # --- HEADLESS НАСТРОЙКИ ДЛЯ СЕРВЕРА ---
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")

    # Используем системный Chrome (не скачиваем через webdriver_manager)
    # На Bothost обычно Chrome установлен по этому пути
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/local/bin/chrome",
    ]

    chrome_binary = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_binary = path
            print(f"✅ Найден Chrome: {chrome_binary}")
            break

    if chrome_binary:
        options.binary_location = chrome_binary
    else:
        print("⚠️ Chrome не найден в системе! Будет использован webdriver_manager")

    # Создаём профиль
    options.add_argument(f"--user-data-dir={os.path.join(os.getcwd(), TEMP_PROFILE_DIR)}")

    try:
        # Пробуем использовать системный ChromeDriver
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ Драйвер создан через системный ChromeDriver")
        return driver
    except:
        print("⚠️ Системный ChromeDriver не найден, пробуем webdriver_manager...")
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            print("✅ Драйвер создан через webdriver_manager")
            return driver
        except Exception as e:
            print(f"❌ Не удалось создать драйвер: {e}")
            raise


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

    delete_temp_profile()

    # Создаём драйвер
    driver = get_driver()

    try:
        print("\n🔓 Открываем ВКонтакте...")
        driver.get("https://vk.com")
        time.sleep(5)
        print("✅ Страница ВК загружена!")

        saved_url = load_url()
        if saved_url:
            print(f"\n🔗 Открываем сохранённую страницу: {saved_url}")
            driver.get(saved_url)
        else:
            print(f"\n🔗 Открываем приложение: {APP_URL}")
            driver.get(APP_URL)

        time.sleep(5)
        print("✅ Страница загружена!")

        current_url = driver.current_url
        print(f"\n📍 Текущий URL: {current_url}")

        if "item&id=14069" not in current_url and "well2.activeusers.ru" not in current_url:
            print("\n⚠️ Вы не на странице с курсом!")
            print(f"   Текущий URL: {current_url}")
            print("   Попробуйте сохранить правильный URL")

        print("\n🚀 Запускаем автоматическое обновление...")
        print(f"   Проверка со случайной задержкой {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} секунд")
        print("   Нажмите Ctrl+C для остановки\n")

        last_notification_time = 0

        while True:
            try:
                click_update_button(driver)
                buy_rate, sell_rate = parse_rate(driver)

                if buy_rate and sell_rate:
                    update_count += 1
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

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
                            print(f"📊 Следующее уведомление через {get_notification_interval(notification_count)} секунд")
                        else:
                            wait_time = int(current_interval - (current_time - last_notification_time))
                            print(f"⏳ Следующее уведомление через {wait_time} сек")
                    else:
                        print(f"⏳ Условия не выполнены:")
                        print(f"   {get_condition_text(buy_rate, sell_rate)}")
                else:
                    print("❌ Не удалось получить курс")

                delay = get_random_delay()
                print(f"⏳ Следующая проверка через {delay} секунд...")
                time.sleep(delay)

            except KeyboardInterrupt:
                print("\n⏹ Остановка по запросу пользователя...")
                break
            except Exception as e:
                print(f"❌ Ошибка в цикле: {e}")
                time.sleep(get_random_delay())

    except KeyboardInterrupt:
        print("\n⏹ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        try:
            driver.quit()
            print("✅ Браузер закрыт")
        except:
            pass


if __name__ == "__main__":
    main()
