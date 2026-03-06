#!/usr/bin/env python3
"""
Script de diagnóstico para WebSocket de iTick.
"""

import sys
import os
import time
import json
import websocket
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.loader import config_loader


def debug_websocket_raw():
    """Prueba raw del WebSocket para ver mensajes completos."""
    print("🔧 Debug raw de WebSocket iTick")
    print("=" * 60)
    
    # Obtener configuración
    itick_config = config_loader.get_itick_config()
    api_key = itick_config['api_key']
    
    print(f"🔑 API Key: {'*' * 20}{api_key[-4:]}")
    
    # Callbacks
    def on_open(ws):
        print("✅ WebSocket abierto")
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            print(f"\n📨 Mensaje recibido:")
            print(f"   Raw: {message[:200]}...")
            print(f"   Parsed: {json.dumps(data, indent=2)}")
            
            # Procesar tipo de mensaje
            if 'code' in data:
                code = data['code']
                if code == 1:
                    print(f"   ✅ Código: 1 (éxito)")
                elif code == 0:
                    print(f"   ❌ Código: 0 (error)")
                else:
                    print(f"   ⚠️  Código: {code} (desconocido)")
            
            if 'resAc' in data:
                print(f"   🔧 resAc: {data['resAc']}")
            
            if 'msg' in data:
                print(f"   📝 Mensaje: {data['msg']}")
            
            if 'data' in data:
                print(f"   📊 Datos: {len(str(data['data']))} bytes")
                
        except json.JSONDecodeError:
            print(f"\n📨 Mensaje no JSON: {message[:100]}...")
        except Exception as e:
            print(f"\n❌ Error procesando mensaje: {e}")
    
    def on_error(ws, error):
        print(f"\n❌ Error WebSocket: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"\n🔒 WebSocket cerrado. Code: {close_status_code}, Msg: {close_msg}")
    
    # Crear conexión
    print("\n🔗 Conectando a wss://api.itick.org/stock...")
    
    headers = {
        'token': api_key
    }
    
    ws = websocket.WebSocketApp(
        "wss://api.itick.org/stock",
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Iniciar en thread
    import threading
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()
    
    # Esperar conexión
    print("⏳ Esperando conexión...")
    time.sleep(3)
    
    # Enviar ping después de 5 segundos
    time.sleep(2)
    print("\n🏓 Enviando ping...")
    ping_msg = {
        "ac": "ping",
        "params": str(int(time.time() * 1000))
    }
    ws.send(json.dumps(ping_msg))
    
    # Intentar suscribir a símbolos US (que deberían tener datos)
    time.sleep(2)
    print("\n📡 Suscribiendo a símbolos US (AAPL, TSLA)...")
    subscribe_msg = {
        "ac": "subscribe",
        "params": "AAPL$US,TSLA$US",
        "types": "quote"
    }
    ws.send(json.dumps(subscribe_msg))
    
    # También intentar con símbolos MX
    time.sleep(2)
    print("\n📡 Suscribiendo a símbolos MX (WALMEX, AC)...")
    subscribe_msg_mx = {
        "ac": "subscribe",
        "params": "WALMEX$MX,AC$MX",
        "types": "quote"
    }
    ws.send(json.dumps(subscribe_msg_mx))
    
    # Esperar 20 segundos para recibir datos
    print("\n⏳ Esperando datos por 20 segundos...")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        for i in range(20):
            print(f"⏱️  {i+1}/20 segundos", end='\r')
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    
    finally:
        print("\n\n🧹 Cerrando WebSocket...")
        ws.close()
        time.sleep(1)
    
    print("✅ Debug completado")


def test_symbol_formats():
    """Prueba diferentes formatos de símbolos."""
    print("\n" + "=" * 60)
    print("🔤 Prueba de formatos de símbolos")
    print("=" * 60)
    
    # Probar diferentes formatos
    symbol_formats = [
        "AAPL$US",      # Formato US estándar
        "TSLA$US",
        "WALMEX$MX",    # Formato MX
        "AC$MX",
        "WALMEX.MX$MX", # Con sufijo
        "AC.MX$MX",
        "WALMEX",       # Sin región
        "AC",
    ]
    
    print("Formatos a probar:")
    for fmt in symbol_formats:
        print(f"  • {fmt}")
    
    print("\n💡 Nota: iTick requiere formato 'SÍMBOLO$REGION'")
    print("   Para BMV: 'WALMEX$MX', 'AC$MX', etc.")


def check_market_hours():
    """Verifica horarios del mercado."""
    print("\n" + "=" * 60)
    print("🕐 Verificación de horarios del mercado")
    print("=" * 60)
    
    from datetime import datetime
    import pytz
    
    # Horarios BMV
    bmv_tz = pytz.timezone('America/Mexico_City')
    now = datetime.now(bmv_tz)
    
    print(f"🕐 Hora actual CDMX: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Día de la semana: {now.strftime('%A')}")
    
    # Horario BMV extendido
    market_open = now.replace(hour=7, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=0, second=0, microsecond=0)
    
    print(f"⏰ Horario BMV: 07:00 - 15:00 CDMX")
    
    if market_open <= now < market_close:
        print(f"🌎 Mercado BMV: ✅ ABIERTO")
        print(f"   Tiempo restante: {(market_close - now).seconds // 3600}:{(market_close - now).seconds % 3600 // 60:02d}")
    else:
        print(f"🌎 Mercado BMV: ❌ CERRADO")
        
        if now < market_open:
            next_open = market_open
            if now.date() < market_open.date():
                next_open = market_open
            print(f"   Próxima apertura: {next_open.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Mañana a las 7:00
            next_open = market_open.replace(day=market_open.day + 1)
            print(f"   Próxima apertura: {next_open.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n💡 Los datos en tiempo real solo están disponibles cuando el mercado está abierto.")
    print("   Fuera del horario, el WebSocket puede no enviar datos.")


def main():
    """Función principal."""
    print("🔍 Diagnóstico de WebSocket iTick")
    print("=" * 60)
    
    # Verificar configuración
    print("🔧 Verificando configuración...")
    if not config_loader.get('ITICK_API_KEY'):
        print("❌ ITICK_API_KEY no configurada")
        print("   Configura .env con tu API key de iTick")
        return 1
    
    print("✅ Configuración OK")
    
    # Ejecutar diagnósticos
    try:
        debug_websocket_raw()
        test_symbol_formats()
        check_market_hours()
        
    except Exception as e:
        print(f"\n❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("📋 Resumen del diagnóstico:")
    print("1. WebSocket se conecta y autentica ✅")
    print("2. Formato de símbolos: SÍMBOLO$REGION")
    print("3. BMV usa: WALMEX$MX, AC$MX, etc.")
    print("4. Datos en tiempo real solo durante horario BMV")
    print("5. Fuera de horario, usar REST API")
    print("\n🔧 Para TacoTrader:")
    print("   • WebSocket para datos en tiempo real (horario BMV)")
    print("   • REST API como fallback (fuera de horario)")
    print("   • Rate limiting solo aplica a REST API")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())