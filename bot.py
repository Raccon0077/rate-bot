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

# --- НАСТРОЙКИ ---
GROUP_TOKEN = "vk1.a.8Gc4tpdnYrLN_BRQ1puFlBBWac3X6AivdJGP2S5pNsVIspW2kfn4dWV6nmFh_X8TWKkZm9yzST751CQFdJ84-J30Uq_T_sFoRshtOlgLDlUZ97VAzgDcoj1jh5s5j6ExbTEcNAmNqhgGo6MpjPf8WIPNbyULTIazIJhyLThAHLx8EyLAjyh9Ya8wNrYRK_jyiTqckSnoDHPutcJOk8khpg"

# --- СПИСОК ПОЛУЧАТЕЛЕЙ ---
USER_IDS = [
    212887447,  # Ваш ID
    145156004,
    # Добавляйте других
]

# --- УСЛОВИЯ ДЛЯ ОТПРАВКИ (хотя бы одно) ---
BUY_THRESHOLD = 50000  # Если покупка НИЖЕ этого значения
SELL_THRESHOLD = 60000  # Если продажа ВЫШЕ этого значения

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

# --- ИНТЕРВАЛЫ ---
MIN_CHECK_INTERVAL = 5   # Минимальная задержка (секунд)
MAX_CHECK_INTERVAL = 13  # Максимальная задержка (секунд)

SAVED_URL_FILE = "saved_url.pkl"
TEMP_PROFILE_DIR = "chromedriver_profile"

# --- ИНИЦИАЛИЗАЦИЯ VK ---
vk_session = vk_api.VkApi(token=GROUP_TOKEN)
vk = vk_session.get_api()

update_count = 0
notification_count = 0


def send_vk_message(text):
    """Отправляет сообщение ВСЕМ пользователям из списка"""
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
    """Проверяет условия для отправки уведомления (ХОТЯ БЫ ОДНО)"""
    buy_condition = buy_rate < BUY_THRESHOLD
    sell_condition = sell_rate > SELL_THRESHOLD
    return buy_condition or sell_condition


def get_condition_text(buy_rate, sell_rate):
    """Возвращает текст с выполненными условиями"""
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
    """
    Возвращает интервал между уведомлениями:
    - Первые 2 раза: 5 секунд
    - Затем: 10 секунд
    """
    if notification_count < 2:
        return 5
    else:
        return 10


def get_random_delay():
    """Возвращает случайную задержку от 5 до 13 секунд (без закономерности)"""
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
    print("   - Каждый раз новая, без закономерности")
    print("=" * 60)
    print("📢 ИНТЕРВАЛЫ УВЕДОМЛЕНИЙ:")
    print("   - 1-е и 2-е уведомление: 5 секунд")
    print("   - С 3-го уведомления: 10 секунд")
    print("=" * 60)

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    options.add_argument(f"--user-data-dir={os.path.join(os.getcwd(), TEMP_PROFILE_DIR)}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("\n🔓 Открываем ВКонтакте...")
        driver.get("https://vk.com")
        time.sleep(3)

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
            print("\n" + "=" * 60)
            print("📌 ВЫ НЕ НА СТРАНИЦЕ С КУРСОМ!")
            print("   Сейчас вы на: " + current_url)
            print("=" * 60)
            print("📌 СДЕЛАЙТЕ РУЧНЫМИ ДЕЙСТВИЯМИ:")
            print("   1. Войдите в ВК, если ещё не вошли")
            print("   2. Перейдите на страницу с курсом")
            print("=" * 60)
            print("✅ КОГДА УВИДИТЕ КУРС, нажмите Enter...")
            input()

            new_url = driver.current_url
            print(f"\n💾 Сохраняем URL: {new_url}")
            save_url(new_url)
        else:
            print("✅ Вы уже на странице с курсом!")

        print("\n" + "=" * 60)
        print("📌 ПРОВЕРЬТЕ, ЧТО ВЫ ВИДИТЕ КУРС ОСКОЛКОВ")
        print("   - На странице должны быть цифры курса")
        print("   - Если видите курс - нажмите Enter")
        print("=" * 60)
        input("✅ НАЖМИТЕ ENTER ДЛЯ ЗАПУСКА АВТО-ОБНОВЛЕНИЯ...")

        print("\n🚀 Запускаем автоматическое обновление...")
        print(f"   Проверка со случайной задержкой {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL} секунд")
        print(f"   Уведомления при выполнении ХОТЯ БЫ ОДНОГО условия!")
        print("   Нажмите Ctrl+C для остановки\n")

        last_notification_time = 0

        while True:
            try:
                click_update_button(driver)
                buy_rate, sell_rate = parse_rate(driver)

                if buy_rate and sell_rate:
                    update_count += 1

                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} #{update_count}: Покупка {buy_rate}, Продажа {sell_rate}")

                    # Проверяем условия (хотя бы одно)
                    if check_conditions(buy_rate, sell_rate):
                        notification_count += 1
                        print(f"🎯 УСЛОВИЯ ВЫПОЛНЕНЫ! (уведомление #{notification_count})")
                        print(f"   {get_condition_text(buy_rate, sell_rate)}")

                        # Получаем текущий интервал для уведомлений
                        current_interval = get_notification_interval(notification_count)

                        # Проверяем, прошло ли достаточно времени с последней отправки
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
                            print(f"⏳ Следующее уведомление через {wait_time} сек (интервал {current_interval} сек)")
                    else:
                        print(f"⏳ Условия не выполнены (нужно хотя бы одно):")
                        print(f"   {get_condition_text(buy_rate, sell_rate)}")
                else:
                    print("❌ Не удалось получить курс")

                # --- СЛУЧАЙНАЯ ЗАДЕРЖКА 5-13 СЕКУНД (полностью случайная) ---
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
