#!/usr/bin/env python3
"""
Script de prueba básico para TacoTrader BMV.
Verifica que los componentes principales funcionen correctamente.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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


def test_config():
    """Prueba la carga de configuración."""
    print("🔧 Probando configuración...")
    
    # Verificar variables críticas
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'ITICK_API_KEY']
    for var in required_vars:
        value = config_loader.get(var)
        if value:
            if isinstance(value, str):
                print(f"  ✅ {var}: {'***' + value[-4:] if len(value) > 4 else '***'}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: NO CONFIGURADO")
    
    print(f"  📁 Config YAML cargada: {len(config_loader.config) > 0}")
    return True


def test_itick_api():
    """Prueba la API de iTick."""
    print("\n📡 Probando API de iTick...")
    
    itick_config = config_loader.get_itick_config()
    provider = ITickProvider(
        api_key=itick_config['api_key'],
        base_url=itick_config['base_url']
    )
    
    # Probar obtención de símbolos
    symbols = provider.get_symbols(force_refresh=True)
    print(f"  ✅ Símbolos obtenidos: {len(symbols)}")
    
    # Probar rate limit status
    rate_status = provider.get_rate_limit_status()
    print(f"  ✅ Rate limit: {rate_status['remaining_requests']}/{rate_status['max_requests']}")
    
    # Probar quote de un símbolo
    if symbols:
        test_symbol = symbols[0]['code']
        quote = provider.get_quote(test_symbol, use_cache=False)
        if quote:
            print(f"  ✅ Quote para {test_symbol}: ${quote.get('p', 'N/A')}")
        else:
            print(f"  ⚠️  No se pudo obtener quote para {test_symbol}")
    
    provider.cleanup()
    return True


def test_symbol_manager():
    """Prueba el gestor de símbolos."""
    print("\n📊 Probando Symbol Manager...")
    
    itick_config = config_loader.get_itick_config()
    provider = ITickProvider(api_key=itick_config['api_key'])
    
    symbol_manager = SymbolManager(
        data_provider=provider,
        data_dir="data",
        max_symbols=10  # Solo 10 para prueba
    )
    
    # Obtener símbolos
    symbols = symbol_manager.get_symbols(force_refresh=True)
    print(f"  ✅ Símbolos gestionados: {len(symbols)}")
    
    # Obtener stats
    stats = symbol_manager.get_stats()
    print(f"  ✅ Stats: {stats['total_symbols']} símbolos, cap. total: ${stats['total_cap_estimated_b_mxn']:.1f}B")
    
    # Obtener códigos
    codes = symbol_manager.get_symbol_codes()
    print(f"  ✅ Códigos: {', '.join(codes[:3])}...")
    
    provider.cleanup()
    return True


def test_market_analyzer():
    """Prueba el analizador de mercado."""
    print("\n📈 Probando Market Analyzer...")
    
    analyzer = MarketAnalyzer(
        min_movement_percent=2.0,
        min_relative_volume=1.8,
        min_atr_percent=2.5,
        min_price_mxn=10.0
    )
    
    # Datos de prueba
    test_quote = {
        'p': 100.50,  # Precio actual
        'ld': 99.80,   # Último precio
        'o': 98.00,    # Apertura
        'h': 102.00,   # Máximo
        'l': 97.50,    # Mínimo
        'v': 1500000,  # Volumen
        'chp': 2.55    # Cambio porcentual
    }
    
    # Calcular indicadores
    indicators = analyzer.calculate_indicators(test_quote)
    print(f"  ✅ Indicadores calculados:")
    print(f"     Movimiento: {indicators['movement_percent']:.2f}%")
    print(f"     Volumen relativo: {indicators['relative_volume']:.2f}x")
    print(f"     ATR: {indicators['atr_percent']:.2f}%")
    print(f"     Score: {indicators['total_score']:.2f}")
    
    # Evaluar criterios
    test_data = {
        'symbol': {'code': 'TEST', 'name': 'Test Symbol'},
        'quote': test_quote
    }
    
    passes, reasons = analyzer.evaluate_criteria(test_data, indicators)
    print(f"  ✅ Criterios: {'PASA' if passes else 'NO PASA'}")
    for reason in reasons.values():
        print(f"     {reason}")
    
    # Calcular precios
    prices = analyzer.calculate_entry_exit_prices(test_data, indicators)
    print(f"  ✅ Precios calculados:")
    print(f"     Entrada: ${prices['entry']:.2f}")
    print(f"     Objetivo: ${prices['target']:.2f}")
    print(f"     Stop: ${prices['stop']:.2f}")
    print(f"     R/R: {prices['risk_reward']:.2f}")
    
    return True


def test_market_hours():
    """Prueba el verificador de horarios."""
    print("\n🕐 Probando Market Hours Checker...")
    
    checker = MarketHoursChecker(
        market_timezone="America/Mexico_City",
        open_time="07:00",
        close_time="15:00"
    )
    
    # Obtener status
    status = checker.get_market_status()
    print(f"  ✅ Status mercado:")
    print(f"     Abierto: {status['market_open']}")
    print(f"     Hora: {status['current_time']}")
    print(f"     Día: {status['weekday']}")
    
    if status['market_open']:
        print(f"     Cierra en: {status['time_to_close_minutes']} minutos")
    else:
        print(f"     Próxima apertura: {status.get('next_open_time', 'N/A')}")
    
    return True


def test_telegram_bot():
    """Prueba el bot de Telegram (solo verifica configuración)."""
    print("\n🤖 Probando Telegram Bot (configuración)...")
    
    telegram_config = config_loader.get_telegram_config()
    
    if telegram_config['bot_token'] and telegram_config['chat_id']:
        print(f"  ✅ Configuración Telegram OK")
        print(f"     Bot token: {'***' + telegram_config['bot_token'][-4:]}")
        print(f"     Chat ID: {telegram_config['chat_id']}")
        
        # Solo crear el bot si hay configuración válida
        try:
            bot = TelegramAlertBot(
                bot_token=telegram_config['bot_token'],
                chat_id=telegram_config['chat_id']
            )
            print(f"  ✅ Bot inicializado correctamente")
            bot.cleanup()
        except Exception as e:
            print(f"  ⚠️  Error inicializando bot: {e}")
            return False
        
        return True
    else:
        print(f"  ⚠️  Configuración Telegram incompleta")
        return False


def main():
    """Función principal de pruebas."""
    print("🌮 TacoTrader BMV - Pruebas de componentes")
    print("=" * 50)
    
    tests = [
        ("Configuración", test_config),
        ("API iTick", test_itick_api),
        ("Symbol Manager", test_symbol_manager),
        ("Market Analyzer", test_market_analyzer),
        ("Market Hours", test_market_hours),
        ("Telegram Bot", test_telegram_bot),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ Error en {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📋 Resumen de pruebas:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"  {status} {test_name}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ¡Todas las pruebas pasaron! TacoTrader está listo.")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa la configuración.")
        return 1


if __name__ == "__main__":
    sys.exit(main())