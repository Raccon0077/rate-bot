def get_rate_from_web():
    """Получает курс через HTTP-запрос с имитацией кнопок"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        session = requests.Session()
        
        print("🌐 Переходим на страницу...")
        session.get(APP_URL, headers=headers)
        time.sleep(1)
        
        print("🔄 Нажимаем 'Узнать курс'...")
        learn_data = {
            'act': 'item',
            'id': '14069',
            'program': '51164l9l1809791bb20cc8f8',
            'action': 'learn'
        }
        session.post(APP_URL, data=learn_data, headers=headers)
        time.sleep(1)
        
        print("🔄 Нажимаем 'Обновить курс'...")
        update_data = {
            'act': 'item',
            'id': '14069',
            'action': 'update'
        }
        session.post(APP_URL, data=update_data, headers=headers)
        time.sleep(1)
        
        print("📥 Получаем страницу с курсом...")
        response = session.get(APP_URL, headers=headers)
        response.raise_for_status()
        
        html = response.text
        
        # --- ВЫВОДИМ HTML В ЛОГИ ---
        print("=" * 60)
        print("📄 HTML страницы (первые 1000 символов):")
        print("=" * 60)
        print(html[:1000])
        print("=" * 60)
        print("📄 Конец HTML")
        print("=" * 60)
        # --- КОНЕЦ БЛОКА ---
        
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("📄 Сохранён debug.html")
        
        # Убираем эмодзи и лишние пробелы
        clean_html = re.sub(r'[🟢🔴💎🌕]', '', html)
        clean_html = re.sub(r'\s+', ' ', clean_html)
        
        # Ищем курс
        buy_match = re.search(r'Покупка:\s*([0-9]+)\s*=>\s*([0-9]+)', clean_html)
        sell_match = re.search(r'Продажа:\s*([0-9]+)\s*=>\s*([0-9]+)', clean_html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(2))
            print(f"✅ Найден курс: покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        # Альтернативный поиск по строкам
        lines = clean_html.split('\n')
        buy_rate = None
        sell_rate = None
        
        for line in lines:
            if 'Покупка' in line:
                numbers = re.findall(r'([0-9]+)', line)
                if numbers:
                    buy_rate = int(numbers[0])
                    print(f"   Найдена покупка: {buy_rate}")
            if 'Продажа' in line:
                numbers = re.findall(r'([0-9]+)', line)
                if numbers:
                    sell_rate = int(numbers[1]) if len(numbers) > 1 else int(numbers[0])
                    print(f"   Найдена продажа: {sell_rate}")
        
        if buy_rate and sell_rate:
            print(f"✅ Найден курс (альт): покупка {buy_rate}, продажа {sell_rate}")
            return buy_rate, sell_rate
        
        print("⚠️ Курс не найден на странице")
        return None, None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None, None
