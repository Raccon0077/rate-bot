def get_rate_from_web():
    """Получает курс через HTTP-запрос с куками"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Добавьте свои куки из браузера
        cookies = {
            'remixsid': 'ваша_кука_сессии_здесь',
        }
        
        response = requests.get(APP_URL, headers=headers, cookies=cookies, timeout=15)
        response.raise_for_status()
        
        html = response.text
        
        # Сохраняем HTML для отладки
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("📄 Сохранён debug.html для анализа")
        
        # Ищем курс
        buy_match = re.search(r'Покупка[^0-9]*([0-9]+)\s*=>', html)
        sell_match = re.search(r'Продажа[^0-9]*100\s*=>\s*[^0-9]*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            return buy_rate, sell_rate
        
        # Альтернативный поиск
        buy_match = re.search(r'Покупка:\s*([0-9]+)', html)
        sell_match = re.search(r'Продажа:\s*100\s*=>\s*([0-9]+)', html)
        
        if buy_match and sell_match:
            buy_rate = int(buy_match.group(1))
            sell_rate = int(sell_match.group(1))
            return buy_rate, sell_rate
        
        return None, None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None, None
