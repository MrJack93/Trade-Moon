import ccxt

def connect_and_check_balance():
    # Ваши реальные демо-ключи
    api_key = 'WwpXxSMYNUmsO0KKf0BwW7LTjFWqcDEmlPVlyVwUYK3Q9MkRWXiaX11qUfBIkbvc'
    secret_key = 'el5AQrUqJKuW96cqb5Ht9pNOtzU1u9RBIYVcyNjYeZGLkNjmVC8vKAiWTquWhufO'
    
    try:
        # Создаем подключение к основной торговой платформе
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'options': {
                'defaultType': 'future',  # Для фьючерсов
            },
            'enableRateLimit': True,
        })
        
        # Включаем демо-торговлю (ВАЖНО!)
        exchange.enable_demo_trading(True)
        
        print("✅ Подключение к новой демо-среде Binance установлено!")
        
        # Проверяем баланс
        balance = exchange.fetch_balance()
        
        print("\n💰 БАЛАНС ДЕМО-СЧЕТА:")
        print("=" * 50)
        
        # Выводим основные валюты
        currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'BUSD']
        
        for currency in currencies:
            if currency in balance:
                print(f"{currency}:")
                print(f"  Свободно: {balance[currency]['free']}")
                print(f"  Используется: {balance[currency]['used']}")
                print(f"  Всего: {balance[currency]['total']}")
                print("-" * 30)
        
        # Показываем общий баланс
        total_balance = balance['total']
        print(f"\n📊 ОБЩИЙ БАЛАНС:")
        for asset, amount in total_balance.items():
            if amount > 0:
                print(f"  {asset}: {amount}")
        
        return exchange
        
    except ccxt.AuthenticationError:
        print("❌ Ошибка аутентификации. Проверьте API ключи!")
    except ccxt.NetworkError:
        print("❌ Ошибка сети. Проверьте интернет-соединение!")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")

# Дополнительные функции для тестирования
def test_demo_trading(exchange):
    """Тестирование демо-торговли"""
    try:
        # Получаем информацию о рынке
        symbol = 'BTC/USDT'
        ticker = exchange.fetch_ticker(symbol)
        print(f"\n🎯 ТЕКУЩАЯ ЦЕНА {symbol}: {ticker['last']}")
        
        # Проверяем открытые ордера
        open_orders = exchange.fetch_open_orders(symbol)
        print(f"📋 Открытые ордера: {len(open_orders)}")
        
        # Проверяем позиции
        positions = exchange.fetch_positions([symbol])
        open_positions = [p for p in positions if p['contracts'] > 0]
        print(f"📈 Открытые позиции: {len(open_positions)}")
        
    except Exception as e:
        print(f"⚠️ Ошибка при тестировании: {e}")

# Запускаем проверку
if __name__ == "__main__":
    exchange = connect_and_check_balance()
    
    if exchange:
        # Дополнительное тестирование
        test_demo_trading(exchange)
        
        print("\n🎉 Демо-счет готов к использованию!")