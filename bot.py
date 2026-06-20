import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

print("🚀 Бот запускается...")

APP_URL = "https://well2.activeusers.ru/app.php?act=item&id=14069&sign=fm3sSt9ZgyYAmqEOmHBLD4ipiP9ZmcFlwebNNJQYzRo&vk_access_token_settings=&vk_app_id=6987489&vk_are_notifications_enabled=0&vk_group_id=182985865&vk_is_app_user=1&vk_is_favorite=0&vk_language=ru&vk_platform=desktop_web&vk_ref=other&vk_ts=1781869457&vk_user_id=212887447&vk_viewer_group_role=member&back=act:user"

driver = None

try:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("🌐 Открываем страницу...")
    driver.get(APP_URL)
    time.sleep(5)
    
    print("🔄 Нажимаем 'Узнать курс'...")
    try:
        learn_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Узнать курс')]")
        learn_btn.click()
        print("   ✅ Нажата кнопка 'Узнать курс'")
        time.sleep(3)
    except Exception as e:
        print(f"   ⚠️ Кнопка 'Узнать курс' не найдена: {e}")
    
    print("🔄 Нажимаем 'Обновить курс'...")
    try:
        update_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Обновить курс')]")
        update_btn.click()
        print("   ✅ Нажата кнопка 'Обновить курс'")
        time.sleep(3)
    except Exception as e:
        print(f"   ⚠️ Кнопка 'Обновить курс' не найдена: {e}")
    
    print("📄 Сохраняем HTML...")
    html = driver.page_source
    
    print("🔍 Ищем курс...")
    
    # --- ПАРСИМ ПОКУПКУ ---
    buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
    buy_rate = int(buy_match.group(1)) if buy_match else None
    print(f"   Покупка: {buy_rate}")
    
    # --- ПАРСИМ ПРОДАЖУ ---
    sell_match = re.search(r'Продажа[^0-9]*([0-9]+)[^0-9]*=>[^0-9]*([0-9]+)', html)
    if sell_match:
        sell_rate = int(sell_match.group(2))  # Берём второе число
        print(f"   Продажа: {sell_rate}")
    else:
        # Если не нашлось, пробуем упрощённый поиск
        sell_match = re.search(r'Продажа[^0-9]*=>[^0-9]*([0-9]+)', html)
        if sell_match:
            sell_rate = int(sell_match.group(1))
            print(f"   Продажа (упрощённо): {sell_rate}")
        else:
            sell_rate = None
            print("   Продажа: не найдена")
    
    # --- ВЫВОД РЕЗУЛЬТАТА ---
    if buy_rate and sell_rate:
        print(f"\n✅ НАЙДЕН КУРС:\n   🟢 Покупка: {buy_rate} => 100 оск.\n   🔴 Продажа: 100 => {sell_rate} оск.\n")
    else:
        print("\n❌ КУРС НЕ НАЙДЕН")
        print(f"   buy_rate: {buy_rate}")
        print(f"   sell_rate: {sell_rate}")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
finally:
    if driver:
        driver.quit()
        print("✅ Браузер закрыт")
