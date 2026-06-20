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
    
    print("📄 Сохраняем HTML...")
    html = driver.page_source
    
    print("🔍 Ищем курс...")
    
    # Ищем числа
    numbers = re.findall(r'\b([0-9]{4,6})\b', html)
    print(f"Найдены числа: {numbers[:20]}")
    
    # Ищем "Покупка"
    if 'Покупка' in html:
        pos = html.find('Покупка')
        print(f"Покупка: {html[pos:pos+200]}")
    else:
        print("❌ 'Покупка' не найдена")
    
    if 'Продажа' in html:
        pos = html.find('Продажа')
        print(f"Продажа: {html[pos:pos+200]}")
    else:
        print("❌ 'Продажа' не найдена")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
finally:
    if driver:
        driver.quit()
        print("✅ Браузер закрыт")
