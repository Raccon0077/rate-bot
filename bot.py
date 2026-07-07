def get_rate_with_selenium(driver):
    """Получение курса с поиском кнопки"""
    global last_buy_rate, last_sell_rate, last_rate_time
    
    current_time = time.time()
    if last_buy_rate and last_sell_rate and (current_time - last_rate_time) < RATE_CACHE_TTL:
        print("   ⚡ Кэш")
        return last_buy_rate, last_sell_rate
    
    try:
        # ПЕРЕХОДИМ НА СТРАНИЦУ
        driver.get(APP_URL)
        time.sleep(2)
        
        # 🔍 ПРОВЕРЯЕМ, ЕСТЬ ЛИ КНОПКА
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        if "Обновить курс" not in page_text:
            print("   ⚠️ Кнопка 'Обновить курс' не найдена на странице")
            print(f"   📄 Текст страницы: {page_text[:300]}")
            
            # Пробуем найти ссылку на биржу или обмен
            try:
                exchange_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Биржа') or contains(text(), 'Обмен')]")
                exchange_link.click()
                print("   🔄 Переход по ссылке 'Биржа/Обмен'")
                time.sleep(2)
            except:
                pass
            
            # Пробуем найти кнопку снова
            try:
                buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Обновить') or contains(text(), 'Курс')]")
                for btn in buttons:
                    if btn.is_displayed():
                        btn.click()
                        print(f"   ✅ Нажата кнопка: {btn.text[:30]}")
                        time.sleep(1)
                        break
            except:
                pass
        
        # Кликаем кнопку
        click_update_button(driver)
        
        # Ждем обновления
        time.sleep(1)
        
        # Получаем HTML
        html = driver.execute_script("return document.documentElement.outerHTML;")
        
        # 🔍 СОХРАНЯЕМ ДЛЯ ОТЛАДКИ
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Ищем курс (разные варианты)
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
