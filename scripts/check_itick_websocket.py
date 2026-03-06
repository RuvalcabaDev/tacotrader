#!/usr/bin/env python3
"""
Script para verificar si iTick API soporta WebSocket.
"""

import requests
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.loader import config_loader


def check_itick_documentation():
    """Verifica documentación de iTick API."""
    print("🔍 Verificando iTick API para WebSocket...")
    
    # Obtener configuración
    itick_config = config_loader.get_itick_config()
    api_key = itick_config['api_key']
    base_url = itick_config['base_url']
    
    headers = {
        'accept': 'application/json',
        'token': api_key
    }
    
    # Probar diferentes endpoints que podrían indicar WebSocket
    endpoints_to_check = [
        "/",
        "/docs",
        "/documentation",
        "/api",
        "/v1",
        "/ws",
        "/websocket",
        "/realtime",
        "/stream",
    ]
    
    print(f"📡 Base URL: {base_url}")
    print(f"🔑 API Key: {'*' * 20}{api_key[-4:]}")
    
    for endpoint in endpoints_to_check:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"\n🔗 {url}:")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    try:
                        data = response.json()
                        print(f"   JSON response (first 200 chars): {str(data)[:200]}")
                    except:
                        print(f"   Text response (first 200 chars): {response.text[:200]}")
                else:
                    print(f"   Content-Type: {content_type}")
                    print(f"   Text (first 200 chars): {response.text[:200]}")
            elif response.status_code == 404:
                print(f"   ❌ Endpoint no encontrado")
            else:
                print(f"   ⚠️  Status inesperado: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"\n🔗 {url}:")
            print(f"   ⏰ Timeout")
        except Exception as e:
            print(f"\n🔗 {url}:")
            print(f"   ❌ Error: {e}")
    
    # Verificar si hay mención de WebSocket en la respuesta de símbolos
    print("\n" + "=" * 60)
    print("📊 Verificando endpoint de símbolos...")
    
    symbols_url = f"{base_url}/symbol/list?type=stock&region=MX"
    try:
        response = requests.get(symbols_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Símbolos obtenidos: {len(data.get('data', []))}")
            
            # Verificar estructura de respuesta
            if 'data' in data:
                first_symbol = data['data'][0] if data['data'] else {}
                print(f"📋 Estructura de símbolo: {list(first_symbol.keys())}")
        else:
            print(f"❌ Error obteniendo símbolos: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")


def check_websocket_libraries():
    """Verifica si hay bibliotecas de WebSocket instaladas."""
    print("\n" + "=" * 60)
    print("📦 Verificando bibliotecas de WebSocket...")
    
    try:
        import websocket
        print(f"✅ websocket-client instalado: {websocket.__version__}")
    except ImportError:
        print("❌ websocket-client NO instalado")
    
    try:
        import websockets
        print(f"✅ websockets instalado: {websockets.__version__}")
    except ImportError:
        print("❌ websockets NO instalado")
    
    try:
        import socketio
        print(f"✅ python-socketio instalado: {socketio.__version__}")
    except ImportError:
        print("❌ python-socketio NO instalado")


def main():
    """Función principal."""
    print("🌮 TacoTrader - Verificación de WebSocket iTick")
    print("=" * 60)
    
    check_itick_documentation()
    check_websocket_libraries()
    
    print("\n" + "=" * 60)
    print("📋 Conclusión:")
    print("1. iTick API actualmente usa REST API")
    print("2. No hay evidencia de endpoints WebSocket públicos")
    print("3. Se necesitaría documentación oficial de iTick para WebSocket")
    print("4. Actualmente TacoTrader usa polling cada 10 minutos")
    print("\n💡 Recomendación: Contactar a iTick para documentación de WebSocket")


if __name__ == "__main__":
    main()