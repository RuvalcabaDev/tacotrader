#!/usr/bin/env python3
"""
Script para probar el WebSocket de iTick.
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.loader import config_loader
from data.itick_provider import ITickProvider
from data.websocket_manager import WebSocketManager, WebSocketDataType
from utils.logger import logger


def test_websocket_direct():
    """Prueba directa del WebSocket Manager."""
    print("🔌 Prueba directa de WebSocket Manager")
    print("=" * 60)
    
    # Obtener configuración
    itick_config = config_loader.get_itick_config()
    api_key = itick_config['api_key']
    
    print(f"🔑 API Key: {'*' * 20}{api_key[-4:]}")
    print(f"🌐 URL: wss://api.itick.org/stock")
    
    # Crear WebSocket Manager
    ws_manager = WebSocketManager(
        api_key=api_key,
        base_url="wss://api.itick.org/stock",
        max_symbols=10,
        reconnect_interval=5
    )
    
    # Agregar callback para datos
    def on_quote_data(data):
        symbol = data.get('s', 'Unknown')
        price = data.get('ld', 0)
        change = data.get('chp', 0)
        timestamp = data.get('t', 0)
        
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            time_str = dt.strftime("%H:%M:%S")
        else:
            time_str = "N/A"
        
        print(f"📈 {symbol}: ${price:.2f} ({change:+.2f}%) @ {time_str}")
    
    ws_manager.add_data_callback(WebSocketDataType.QUOTE, on_quote_data)
    
    # Conectar
    print("\n🔗 Conectando a WebSocket...")
    if not ws_manager.connect():
        print("❌ No se pudo conectar al WebSocket")
        return False
    
    print("✅ WebSocket conectado")
    
    # Esperar autenticación
    print("🔐 Esperando autenticación...")
    for i in range(10):
        if ws_manager.authenticated:
            print("✅ WebSocket autenticado")
            break
        time.sleep(1)
    
    if not ws_manager.authenticated:
        print("❌ Timeout en autenticación")
        ws_manager.cleanup()
        return False
    
    # Suscribir a algunos símbolos BMV
    bmv_symbols = ["WALMEX$MX", "AC$MX", "GFNORTE$MX"]  # Formato iTick
    
    print(f"\n📡 Suscribiendo a {len(bmv_symbols)} símbolos BMV...")
    success = ws_manager.subscribe(
        symbols=bmv_symbols,
        data_types=[WebSocketDataType.QUOTE]
    )
    
    if not success:
        print("❌ Error suscribiendo símbolos")
        ws_manager.cleanup()
        return False
    
    print("✅ Símbolos suscritos")
    
    # Esperar datos por 30 segundos
    print("\n⏳ Esperando datos (30 segundos)...")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        start_time = time.time()
        data_count = 0
        
        while time.time() - start_time < 30:
            # Verificar estado
            if not ws_manager.connected:
                print("❌ WebSocket desconectado")
                break
            
            # Mostrar datos recibidos
            all_data = ws_manager.get_all_data()
            if len(all_data) > data_count:
                data_count = len(all_data)
                print(f"📊 Datos recibidos: {data_count} símbolos")
            
            time.sleep(1)
        
        print(f"\n📋 Resumen:")
        print(f"   Tiempo de prueba: {time.time() - start_time:.1f}s")
        print(f"   Datos recibidos: {data_count}")
        print(f"   Estado conexión: {'✅ CONECTADO' if ws_manager.connected else '❌ DESCONECTADO'}")
        print(f"   Autenticado: {'✅ SÍ' if ws_manager.authenticated else '❌ NO'}")
        
        # Mostrar algunos datos
        print(f"\n📈 Datos de muestra:")
        all_data = ws_manager.get_all_data()
        for symbol, data in list(all_data.items())[:3]:
            price = data.get('ld', 0)
            change = data.get('chp', 0)
            print(f"   {symbol}: ${price:.2f} ({change:+.2f}%)")
        
    except KeyboardInterrupt:
        print("\n🛑 Prueba interrumpida por usuario")
    
    finally:
        # Limpiar
        print("\n🧹 Limpiando recursos...")
        ws_manager.cleanup()
        print("✅ Prueba completada")
    
    return True


def test_itick_provider_websocket():
    """Prueba el ITickProvider con WebSocket habilitado."""
    print("\n" + "=" * 60)
    print("📡 Prueba de ITickProvider con WebSocket")
    print("=" * 60)
    
    # Obtener configuración
    itick_config = config_loader.get_itick_config()
    
    # Crear provider con WebSocket habilitado
    print("🔧 Creando ITickProvider con WebSocket...")
    provider = ITickProvider(
        api_key=itick_config['api_key'],
        base_url=itick_config['base_url'],
        use_websocket=True,
        max_symbols=10
    )
    
    # Verificar estado WebSocket
    ws_status = provider.get_websocket_status()
    print(f"🔌 WebSocket habilitado: {'✅ SÍ' if ws_status.get('enabled') else '❌ NO'}")
    print(f"🔗 WebSocket conectado: {'✅ SÍ' if ws_status.get('connected') else '❌ NO'}")
    
    if not ws_status.get('connected'):
        print("⚠️  WebSocket no conectado, usando REST API")
    
    # Obtener algunos símbolos BMV
    print("\n📊 Obteniendo símbolos BMV...")
    symbols = provider.get_symbols(force_refresh=True)
    
    if not symbols:
        print("❌ No se pudieron obtener símbolos")
        provider.cleanup()
        return False
    
    print(f"✅ {len(symbols)} símbolos obtenidos")
    
    # Seleccionar algunos símbolos para probar
    # iTick usa 'c' para código, pero nuestro provider usa 'code'
    test_symbols = []
    for s in symbols[:5]:
        if isinstance(s, dict):
            symbol_code = s.get('c') or s.get('code')
            if symbol_code:
                test_symbols.append(symbol_code)
    
    if not test_symbols:
        print("❌ No se pudieron extraer códigos de símbolos")
        provider.cleanup()
        return False
    print(f"🔍 Probando símbolos: {', '.join(test_symbols)}")
    
    # Probar obtención de quotes
    print("\n📈 Obteniendo quotes...")
    
    for symbol in test_symbols:
        # Intentar obtener via WebSocket primero
        realtime_data = provider.get_realtime_quote(symbol)
        
        if realtime_data:
            print(f"  🔌 {symbol}: WebSocket - ${realtime_data.get('ld', 0):.2f}")
        else:
            # Usar REST API como fallback
            quote = provider.get_quote(symbol, use_cache=False)
            if quote:
                price = quote.get('ld', 0)
                change = quote.get('chp', 0)
                print(f"  📡 {symbol}: REST API - ${price:.2f} ({change:+.2f}%)")
            else:
                print(f"  ❌ {symbol}: No se pudo obtener quote")
    
    # Probar batch quotes
    print("\n📦 Probando batch quotes...")
    batch_results = provider.get_batch_quotes(test_symbols)
    
    successful = sum(1 for v in batch_results.values() if v is not None)
    print(f"✅ {successful}/{len(test_symbols)} quotes obtenidos")
    
    # Mostrar estado final
    print("\n📋 Estado final:")
    final_ws_status = provider.get_websocket_status()
    rate_status = provider.get_rate_limit_status()
    
    print(f"🔌 WebSocket: {'✅ CONECTADO' if final_ws_status.get('connected') else '❌ DESCONECTADO'}")
    print(f"📡 Símbolos suscritos: {final_ws_status.get('subscribed_symbols', 0)}")
    print(f"💾 Cache WebSocket: {final_ws_status.get('data_cache_size', 0)}")
    print(f"🔧 Rate Limit REST: {rate_status['remaining_requests']}/{rate_status['max_requests']}")
    
    # Limpiar
    print("\n🧹 Limpiando provider...")
    provider.cleanup()
    
    return True


def main():
    """Función principal."""
    print("🌮 TacoTrader - Prueba de WebSocket iTick")
    print("=" * 60)
    
    # Verificar configuración
    print("🔧 Verificando configuración...")
    required_vars = ['ITICK_API_KEY']
    missing = []
    
    for var in required_vars:
        if not config_loader.get(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Variables faltantes: {', '.join(missing)}")
        print("   Configura .env con tu API key de iTick")
        return 1
    
    print("✅ Configuración OK")
    
    # Ejecutar pruebas
    print("\n" + "=" * 60)
    
    # Prueba 1: WebSocket directo
    if not test_websocket_direct():
        print("\n⚠️  Prueba directa de WebSocket falló")
    
    # Prueba 2: ITickProvider integrado
    if not test_itick_provider_websocket():
        print("\n⚠️  Prueba de ITickProvider falló")
    
    print("\n" + "=" * 60)
    print("🎉 Pruebas de WebSocket completadas")
    print("\n💡 Conclusión:")
    print("1. WebSocket proporciona datos en tiempo real")
    print("2. TacoTrader usa WebSocket cuando está disponible")
    print("3. REST API se usa como fallback automático")
    print("4. Rate limiting ya no es problema con WebSocket")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())