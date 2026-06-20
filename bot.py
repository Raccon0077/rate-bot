import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    
    # --- ИЩЕМ КНОПКИ ПО РАЗНЫМ СЕЛЕКТОРАМ ---
    print("🔄 Ищем кнопки...")
    
    # Способ 1: По тексту
    try:
        learn_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Узнать курс')]")
        learn_btn.click()
        print("   ✅ Нажата кнопка 'Узнать курс' (по тексту)")
        time.sleep(3)
    except:
        print("   ⚠️ Кнопка 'Узнать курс' не найдена по тексту")
    
    # Способ 2: По классу
    try:
        buttons = driver.find_elements(By.CLASS_NAME, "btn-default")
        for btn in buttons:
            if 'Узнать' in btn.text or 'узнать' in btn.text:
                btn.click()
                print("   ✅ Нажата кнопка 'Узнать курс' (по классу)")
                time.sleep(3)
                break
    except:
        print("   ⚠️ Кнопка 'Узнать курс' не найдена по классу")
    
    # Способ 3: По атрибуту onclick
    try:
        learn_btn = driver.find_element(By.CSS_SELECTOR, "[onclick*='run_program']")
        learn_btn.click()
        print("   ✅ Нажата кнопка 'Узнать курс' (по onclick)")
        time.sleep(3)
    except:
        print("   ⚠️ Кнопка 'Узнать курс' не найдена по onclick")
    
    # --- ТЕПЕРЬ НАЖИМАЕМ "ОБНОВИТЬ КУРС" ---
    try:
        update_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Обновить курс')]")
        update_btn.click()
        print("   ✅ Нажата кнопка 'Обновить курс'")
        time.sleep(3)
    except:
        print("   ⚠️ Кнопка 'Обновить курс' не найдена")
    
    print("📄 Сохраняем HTML...")
    html = driver.page_source
    
    # --- СОХРАНЯЕМ HTML ДЛЯ ОТЛАДКИ ---
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("📄 HTML сохранён в debug.html")
    
    print("🔍 Ищем курс...")
    
    # --- ИЩЕМ В HTML ---
    if 'Покупка' in html:
        pos = html.find('Покупка')
        print(f"✅ 'Покупка' найдена: {html[pos:pos+200]}")
        
        # Парсим покупку
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)', html)
        if buy_match:
            buy_rate = int(buy_match.group(1))
            print(f"   Покупка: {buy_rate}")
    else:
        print("❌ 'Покупка' НЕ найдена")
    
    if 'Продажа' in html:
        pos = html.find('Продажа')
        print(f"✅ 'Продажа' найдена: {html[pos:pos+200]}")
        
        # Парсим продажу
        sell_match = re.search(r'Продажа[^0-9]*=>[^0-9]*([0-9]+)', html)
        if sell_match:
            sell_rate = int(sell_match.group(1))
            print(f"   Продажа: {sell_rate}")
    else:
        print("❌ 'Продажа' НЕ найдена")
    
    # --- ВЫВОДИМ ВСЕ ЧИСЛА ---
    numbers = re.findall(r'\b([0-9]{4,6})\b', html)
    print(f"🔢 Все числа: {numbers[:20]}")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
finally:
    if driver:
        driver.quit()
        print("✅ Браузер закрыт")
