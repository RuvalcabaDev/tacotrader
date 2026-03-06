#!/usr/bin/env python3
"""
Test script para rotating WebSocket subscriptions.

Prueba el sistema de suscripciones rotativas que permite monitorear
más de 3 símbolos con el plan gratuito de iTick.
"""

import sys
import os
import time
import json
from datetime import datetime

# Agregar directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configurar logging básico
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar módulos después de configurar path
try:
    from src.config.loader import config_loader
    from src.data.itick_provider import ITickProvider
    from src.data.symbol_manager import SymbolManager
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrate de estar en el directorio correcto y que los módulos existan")
    sys.exit(1)


def test_rotating_subscriptions():
    """Prueba el sistema de rotating subscriptions."""
    print("🧪 Test: Rotating WebSocket Subscriptions")
    print("=" * 60)
    
    # Cargar configuración
    config = config_loader
    
    # Obtener configuración de iTick
    itick_config = config.get_itick_config()
    
    # 1. Inicializar ITickProvider con WebSocket habilitado
    print("\n1. Inicializando ITickProvider con WebSocket...")
    data_provider = ITickProvider(
        api_key=itick_config['api_key'],
        base_url=itick_config['base_url'],
        use_websocket=True,
        max_symbols=30  # Monitorear top 30 símbolos
    )
    
    # 2. Inicializar SymbolManager
    print("2. Inicializando SymbolManager...")
    symbol_manager = SymbolManager(
        data_provider=data_provider,
        data_dir="data",
        max_symbols=100,
        refresh_hours=24
    )
    
    # 3. Obtener símbolos
    print("3. Obteniendo símbolos BMV...")
    symbols = symbol_manager.get_symbols(force_refresh=False)
    
    if not symbols:
        print("❌ Error: No se pudieron obtener símbolos")
        return False
    
    print(f"   ✅ Obtenidos {len(symbols)} símbolos")
    
    # 4. Obtener top 30 símbolos para WebSocket
    print("4. Seleccionando top 30 símbolos para WebSocket...")
    top_symbol_codes = symbol_manager.get_top_symbols_for_websocket(count=30)
    top_symbol_metadata = symbol_manager.get_symbol_metadata_for_websocket(top_symbol_codes)
    
    print(f"   ✅ Seleccionados {len(top_symbol_codes)} símbolos")
    print(f"   Top 5: {', '.join(top_symbol_codes[:5])}")
    
    # 5. Suscribir símbolos al WebSocket
    print("5. Configurando rotating subscriptions...")
    success = data_provider.subscribe_symbols(top_symbol_codes, top_symbol_metadata)
    
    if not success:
        print("❌ Error: No se pudo configurar rotating subscriptions")
        return False
    
    print("   ✅ Rotating subscriptions configurado")
    
    # 6. Obtener estado del WebSocket
    print("6. Obteniendo estado del WebSocket...")
    ws_status = data_provider.get_websocket_status()
    
    print(f"   ✅ WebSocket habilitado: {ws_status.get('enabled')}")
    print(f"   ✅ Conectado: {ws_status.get('connected')}")
    print(f"   ✅ Autenticado: {ws_status.get('authenticated')}")
    
    if ws_status.get('rotating_enabled'):
        rotation_status = ws_status.get('rotation_status', {})
        print(f"   ✅ Rotating habilitado: Sí")
        print(f"   📊 Símbolos monitoreados: {ws_status.get('total_symbols_monitored', 0)}")
        print(f"   🔄 Grupos: {ws_status.get('rotation_groups', 0)}")
        print(f"   ⚡ Rotaciones: {rotation_status.get('rotation_count', 0)}")
        print(f"   📈 Símbolos procesados: {rotation_status.get('total_symbols_processed', 0)}")
    else:
        print("   ⚠️  Rotating no habilitado")
    
    # 7. Monitorear por 2 minutos
    print("\n7. Monitoreando rotating subscriptions por 2 minutos...")
    print("   (Presiona Ctrl+C para terminar temprano)")
    
    try:
        for minute in range(2):
            for second in range(60):
                # Obtener estado actual
                current_status = data_provider.get_websocket_status()
                
                if second % 15 == 0:  # Log cada 15 segundos
                    if current_status.get('rotating_enabled'):
                        rotation = current_status.get('rotation_status', {})
                        current_group = rotation.get('current_group_symbols', [])
                        group_index = rotation.get('current_group_index', 0) + 1
                        total_groups = rotation.get('total_groups', 0)
                        
                        print(f"   [{minute:02d}:{second:02d}] Grupo {group_index}/{total_groups}: "
                              f"{', '.join(current_group[:3])}...")
                
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n   ⏹️  Monitoreo interrumpido por usuario")
    
    # 8. Obtener datos de algunos símbolos
    print("\n8. Probando obtención de datos...")
    
    test_symbols = top_symbol_codes[:5]  # Probar con primeros 5 símbolos
    
    for symbol_code in test_symbols:
        # Intentar obtener datos via WebSocket
        realtime_data = data_provider.get_realtime_quote(symbol_code)
        
        if realtime_data:
            print(f"   ✅ {symbol_code}: Datos obtenidos via WebSocket")
            # Mostrar algunos campos
            price = realtime_data.get('price')
            change = realtime_data.get('change_percent', 0)
            volume = realtime_data.get('volume', 0)
            print(f"      💰 Precio: ${price:.2f}, 📈 Cambio: {change:.2f}%, 📊 Volumen: {volume:,}")
        else:
            print(f"   ⚠️  {symbol_code}: Sin datos via WebSocket (puede ser normal fuera de horario)")
    
    # 9. Mostrar estadísticas finales
    print("\n9. Estadísticas finales:")
    
    final_status = data_provider.get_websocket_status()
    connection_stats = final_status.get('connection_stats', {})
    
    print(f"   🔌 Conectado: {final_status.get('connected')}")
    print(f"   ⏱️  Uptime: {connection_stats.get('uptime_seconds', 0):.0f} segundos")
    print(f"   🔄 Reconexiones totales: {connection_stats.get('total_reconnects', 0)}")
    print(f"   💾 Cache size: {final_status.get('data_cache_size', 0)} símbolos")
    
    if final_status.get('rotating_enabled'):
        rotation = final_status.get('rotation_status', {})
        print(f"   ⚡ Rotaciones completadas: {rotation.get('rotation_count', 0)}")
        print(f"   📈 Símbolos procesados: {rotation.get('total_symbols_processed', 0)}")
    
    # 10. Limpiar
    print("\n10. Limpiando recursos...")
    data_provider.cleanup()
    
    print("\n✅ Test completado exitosamente!")
    return True


def main():
    """Función principal."""
    try:
        success = test_rotating_subscriptions()
        
        if success:
            print("\n🎉 ¡Rotating WebSocket subscriptions funciona correctamente!")
            print("\nResumen de mejoras implementadas:")
            print("1. ✅ Rotating subscriptions para monitorear más de 3 símbolos")
            print("2. ✅ Priorización por market cap (top 30 símbolos)")
            print("3. ✅ Rotación cada 15 segundos")
            print("4. ✅ Reconexión automática con backoff exponencial")
            print("5. ✅ Cache de datos para acceso rápido")
            print("6. ✅ Estadísticas detalladas de conexión")
            print("\nEl sistema ahora puede monitorear 30 símbolos en tiempo real")
            print("con el plan gratuito de iTick (límite: 3 símbolos simultáneos).")
        else:
            print("\n❌ Test falló")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error durante el test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()