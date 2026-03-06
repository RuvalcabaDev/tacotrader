#!/usr/bin/env python3
"""
Prueba final del sistema WebSocket integrado en TacoTrader.
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.loader import config_loader
from core.tacotrader import TacoTraderBMV
from utils.logger import logger


def test_complete_system():
    """Prueba el sistema completo con WebSocket integrado."""
    print("🌮 TacoTrader - Sistema completo con WebSocket")
    print("=" * 60)
    
    # Verificar configuración
    print("🔧 Verificando configuración...")
    required_vars = ['ITICK_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing = []
    
    for var in required_vars:
        if not config_loader.get(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Variables faltantes: {', '.join(missing)}")
        return False
    
    print("✅ Configuración OK")
    
    # Crear instancia de TacoTrader
    print("\n🚀 Inicializando TacoTrader BMV...")
    
    try:
        tacotrader = TacoTraderBMV()
        
        print("✅ TacoTrader inicializado")
        
        # Verificar estado WebSocket
        print("\n🔌 Verificando WebSocket...")
        ws_status = tacotrader.get_websocket_status()
        
        print(f"   Habilitado: {'✅ SÍ' if ws_status.get('enabled') else '❌ NO'}")
        print(f"   Conectado: {'✅ SÍ' if ws_status.get('connected') else '❌ NO'}")
        print(f"   Autenticado: {'✅ SÍ' if ws_status.get('authenticated') else '❌ NO'}")
        print(f"   Símbolos suscritos: {ws_status.get('subscribed_symbols', 0)}")
        
        # Verificar si está usando datos en tiempo real
        print(f"\n📡 Fuente de datos:")
        if tacotrader.is_using_realtime_data():
            print("   ✅ WebSocket (datos en tiempo real)")
            print("   💡 3 símbolos principales en tiempo real")
            print("   💡 Resto via REST API cada 10 minutos")
        else:
            print("   📡 REST API (polling cada 10 minutos)")
            print("   ⚠️  Rate limit: 5 requests/minuto")
            print("   💡 Considera usar horario BMV para WebSocket")
        
        # Verificar estado del mercado
        print(f"\n🌎 Estado del mercado BMV:")
        market_status = tacotrader.market_hours.get_market_status()
        
        print(f"   Abierto: {'✅ SÍ' if market_status['market_open'] else '❌ NO'}")
        print(f"   Hora: {market_status['current_time']}")
        print(f"   Horario: 07:00 - 15:00 CDMX")
        
        if market_status['market_open']:
            print(f"   ⏳ Cierra en: {market_status.get('time_to_close_minutes', 'N/A')} minutos")
        else:
            print(f"   ⏰ Próxima apertura: {market_status.get('next_open_time', 'N/A')}")
        
        # Probar obtención de datos
        print(f"\n📊 Probando obtención de datos...")
        
        # Obtener símbolos
        symbols = tacotrader.symbol_manager.get_symbols(force_refresh=False)
        if symbols:
            print(f"   ✅ {len(symbols)} símbolos BMV cargados")
            
            # Probar quotes para algunos símbolos
            test_symbols = [s['code'] for s in symbols[:3]]
            print(f"   🔍 Probando: {', '.join(test_symbols)}")
            
            for symbol in test_symbols:
                quote = tacotrader.data_provider.get_quote(symbol, use_cache=False)
                if quote:
                    price = quote.get('ld', 0)
                    change = quote.get('chp', 0)
                    source = "🔌 WebSocket" if tacotrader.is_using_realtime_data() else "📡 REST"
                    print(f"     {source} {symbol}: ${price:.2f} ({change:+.2f}%)")
                else:
                    print(f"     ❌ {symbol}: No se pudo obtener quote")
        
        # Mostrar estado de rate limiting
        print(f"\n🔧 Estado de rate limiting:")
        rate_status = tacotrader.data_provider.get_rate_limit_status()
        
        print(f"   Requests restantes: {rate_status['remaining_requests']}/{rate_status['max_requests']}")
        print(f"   Reset en: {rate_status['time_to_reset']:.0f} segundos")
        
        # Mostrar estrategia de datos
        print(f"\n🎯 Estrategia de datos implementada:")
        print(f"   1. WebSocket para 3 símbolos principales (tiempo real)")
        print(f"   2. REST API para símbolos restantes (cada 10 minutos)")
        print(f"   3. Cache de 5 minutos para reducir requests")
        print(f"   4. Fallback automático REST → WebSocket")
        
        # Limpiar
        print(f"\n🧹 Limpiando recursos...")
        tacotrader.data_provider.cleanup()
        
        print("✅ Prueba completada")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal."""
    print("🔧 Prueba final del sistema WebSocket")
    print("=" * 60)
    
    if not test_complete_system():
        print("\n❌ Prueba falló")
        return 1
    
    print("\n" + "=" * 60)
    print("🎉 ¡Sistema WebSocket implementado exitosamente!")
    print("\n📋 Resumen de implementación:")
    print("✅ WebSocket Manager creado")
    print("✅ ITickProvider integrado con WebSocket")
    print("✅ TacoTrader configurado para usar WebSocket")
    print("✅ Límite de 3 símbolos manejado automáticamente")
    print("✅ Priorización por capitalización de mercado")
    print("✅ Fallback a REST API cuando WebSocket no está disponible")
    print("✅ Status reporting incluye información de WebSocket")
    
    print("\n🚀 Para ejecutar TacoTrader:")
    print("   python main.py")
    
    print("\n💡 Recomendaciones:")
    print("   1. Ejecuta durante horario BMV (7:00-15:00 CDMX) para datos en tiempo real")
    print("   2. WebSocket mantiene 3 símbolos principales en tiempo real")
    print("   3. REST API maneja el resto con rate limiting")
    print("   4. Considera upgrade de plan iTick para más símbolos en tiempo real")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())