#!/usr/bin/env python3
"""
Script de verificación de salud para TacoTrader BMV.
Verifica que todos los componentes estén funcionando correctamente.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.loader import config_loader
from data.itick_provider import ITickProvider
from data.symbol_manager import SymbolManager
from screener.analyzer import MarketAnalyzer
from alerts.telegram_bot import TelegramAlertBot
from scheduler.market_hours import MarketHoursChecker
from utils.logger import logger


def check_config():
    """Verifica la configuración."""
    print("🔧 Verificando configuración...")
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'ITICK_API_KEY']
    missing = []
    
    for var in required_vars:
        if not config_loader.get(var):
            missing.append(var)
    
    if missing:
        print(f"  ❌ Variables faltantes: {', '.join(missing)}")
        return False
    
    print("  ✅ Configuración OK")
    return True


def check_itick_api():
    """Verifica la API de iTick."""
    print("\n📡 Verificando API de iTick...")
    
    try:
        itick_config = config_loader.get_itick_config()
        provider = ITickProvider(
            api_key=itick_config['api_key'],
            base_url=itick_config['base_url']
        )
        
        # Probar obtención de símbolos
        symbols = provider.get_symbols(force_refresh=True)
        
        if symbols:
            print(f"  ✅ API iTick OK ({len(symbols)} símbolos)")
            provider.cleanup()
            return True
        else:
            print("  ❌ No se pudieron obtener símbolos")
            provider.cleanup()
            return False
            
    except Exception as e:
        print(f"  ❌ Error en API iTick: {e}")
        return False


def check_telegram():
    """Verifica Telegram."""
    print("\n🤖 Verificando Telegram...")
    
    try:
        telegram_config = config_loader.get_telegram_config()
        
        if not telegram_config['bot_token'] or not telegram_config['chat_id']:
            print("  ❌ Configuración Telegram incompleta")
            return False
        
        bot = TelegramAlertBot(
            bot_token=telegram_config['bot_token'],
            chat_id=telegram_config['chat_id']
        )
        
        # Probar conexión
        bot_info = bot.bot.get_me()
        if bot_info:
            print(f"  ✅ Telegram OK (Bot: @{bot_info.username})")
            bot.cleanup()
            return True
        else:
            print("  ❌ No se pudo obtener info del bot")
            bot.cleanup()
            return False
            
    except Exception as e:
        print(f"  ❌ Error en Telegram: {e}")
        return False


def check_components():
    """Verifica todos los componentes."""
    print("\n⚙️ Verificando componentes...")
    
    components_ok = True
    
    try:
        # Market Analyzer
        analyzer = MarketAnalyzer()
        print("  ✅ Market Analyzer OK")
    except Exception as e:
        print(f"  ❌ Market Analyzer: {e}")
        components_ok = False
    
    try:
        # Market Hours
        market_config = config_loader.get_market_config()
        market_hours = MarketHoursChecker(
            market_timezone=market_config.get('timezone', 'America/Mexico_City'),
            open_time=market_config.get('open_time', '07:00'),
            close_time=market_config.get('close_time', '15:00')
        )
        print("  ✅ Market Hours OK")
    except Exception as e:
        print(f"  ❌ Market Hours: {e}")
        components_ok = False
    
    try:
        # Symbol Manager
        itick_config = config_loader.get_itick_config()
        provider = ITickProvider(api_key=itick_config['api_key'])
        symbol_manager = SymbolManager(
            data_provider=provider,
            data_dir="data",
            max_symbols=10
        )
        print("  ✅ Symbol Manager OK")
        provider.cleanup()
    except Exception as e:
        print(f"  ❌ Symbol Manager: {e}")
        components_ok = False
    
    return components_ok


def main():
    """Función principal."""
    print("🌮 TacoTrader BMV - Verificación de Salud")
    print("=" * 50)
    
    checks = [
        ("Configuración", check_config),
        ("API iTick", check_itick_api),
        ("Telegram", check_telegram),
        ("Componentes", check_components),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            success = check_func()
            results.append((check_name, success))
        except Exception as e:
            print(f"  ❌ Error en {check_name}: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 50)
    print("📋 Resultados de verificación:")
    
    all_passed = True
    for check_name, success in results:
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"  {status} {check_name}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ¡Todas las verificaciones pasaron! TacoTrader está listo.")
        return 0
    else:
        print("⚠️  Algunas verificaciones fallaron. Revisa los errores.")
        return 1


if __name__ == "__main__":
    sys.exit(main())