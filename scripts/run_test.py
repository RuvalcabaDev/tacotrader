#!/usr/bin/env python3
"""
Script para ejecutar una prueba completa de TacoTrader BMV.
Ejecuta el screener una vez y muestra resultados.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.loader import config_loader
from data.itick_provider import ITickProvider
from data.symbol_manager import SymbolManager
from screener.analyzer import MarketAnalyzer
from alerts.telegram_bot import TelegramAlertBot


def run_test():
    """Ejecuta prueba completa."""
    print("🌮 TacoTrader BMV - Prueba Completa")
    print("=" * 60)
    
    # 1. Inicializar componentes
    print("\n1. 🔧 Inicializando componentes...")
    
    itick_config = config_loader.get_itick_config()
    telegram_config = config_loader.get_telegram_config()
    
    data_provider = ITickProvider(
        api_key=itick_config['api_key'],
        base_url=itick_config['base_url'],
        max_symbols=20  # Solo 20 para prueba rápida
    )
    
    symbol_manager = SymbolManager(
        data_provider=data_provider,
        data_dir="data",
        max_symbols=20,
        refresh_hours=24
    )
    
    analyzer = MarketAnalyzer(
        min_movement_percent=2.0,
        min_relative_volume=1.8,
        min_atr_percent=2.5,
        min_price_mxn=10.0
    )
    
    telegram_bot = TelegramAlertBot(
        bot_token=telegram_config['bot_token'],
        chat_id=telegram_config['chat_id']
    )
    
    print("   ✅ Componentes inicializados")
    
    # 2. Obtener símbolos
    print("\n2. 📊 Obteniendo símbolos BMV...")
    symbols = symbol_manager.get_symbols(force_refresh=True)
    symbol_codes = [s['code'] for s in symbols]
    
    print(f"   ✅ Obtenidos {len(symbol_codes)} símbolos")
    print(f"   📋 Primeros 5: {', '.join(symbol_codes[:5])}")
    
    # 3. Obtener quotes
    print("\n3. 📡 Obteniendo quotes...")
    quotes = data_provider.get_batch_quotes(symbol_codes)
    
    valid_quotes = sum(1 for q in quotes.values() if q is not None)
    print(f"   ✅ Obtenidos {valid_quotes} quotes válidos de {len(symbol_codes)}")
    
    # 4. Analizar símbolos
    print("\n4. 📈 Analizando símbolos...")
    analyses = []
    
    for symbol_code, quote in quotes.items():
        if quote is None:
            continue
        
        symbol_info = symbol_manager.get_symbol_info(symbol_code)
        if not symbol_info:
            continue
        
        symbol_data = {
            'symbol': symbol_info,
            'quote': quote
        }
        
        analysis = analyzer.analyze_symbol(symbol_data)
        if analysis:
            analyses.append(analysis)
    
    print(f"   ✅ Analizados {len(analyses)} símbolos")
    
    # 5. Filtrar oportunidades
    print("\n5. 🎯 Filtrando oportunidades...")
    top_opportunities = analyzer.filter_and_rank_opportunities(
        analyses,
        top_n=5
    )
    
    print(f"   ✅ Encontradas {len(top_opportunities)} oportunidades")
    
    # 6. Mostrar resultados
    print("\n6. 📋 Resultados:")
    print("   " + "-" * 50)
    
    if top_opportunities:
        for i, opp in enumerate(top_opportunities, 1):
            symbol = opp['symbol']
            indicators = opp['indicators']
            prices = opp['prices']
            
            print(f"   {i}. {symbol}")
            print(f"      Movimiento: {indicators['movement_percent']:+.2f}%")
            print(f"      Volumen: {indicators['relative_volume']:.1f}x")
            print(f"      ATR: {indicators['atr_percent']:.2f}%")
            print(f"      Score: {indicators['total_score']:.2f}")
            print(f"      Probabilidad: {indicators['probability_percent']:.1f}%")
            print(f"      Precios: ${prices['entry']:.2f} → ${prices['target']:.2f}")
            print(f"      Stop: ${prices['stop']:.2f} (R/R: {prices['risk_reward']:.2f})")
            print()
    else:
        print("   ⚠️  No se encontraron oportunidades que cumplan los criterios")
    
    # 7. Enviar alertas de prueba (opcional)
    print("\n7. 🤖 Enviando alertas de prueba...")
    
    send_alerts = input("   ¿Enviar alertas a Telegram? (s/n): ").lower().strip() == 's'
    
    if send_alerts and top_opportunities:
        print("   📤 Enviando alertas...")
        results = telegram_bot.send_batch_alerts(top_opportunities[:2])  # Solo 2 para prueba
        
        successful = sum(1 for success in results.values() if success)
        print(f"   ✅ Alertas enviadas: {successful} exitosas de {len(results)}")
    else:
        print("   ⏭️  Saltando envío de alertas")
    
    # 8. Mostrar métricas
    print("\n8. 📊 Métricas finales:")
    print("   " + "-" * 50)
    
    if analyses:
        total_symbols = len(analyses)
        passing_symbols = len(top_opportunities)
        pass_rate = (passing_symbols / total_symbols * 100) if total_symbols > 0 else 0
        
        avg_movement = sum(a['indicators']['movement_percent'] for a in analyses) / total_symbols
        avg_volume = sum(a['indicators']['relative_volume'] for a in analyses) / total_symbols
        avg_score = sum(a['indicators']['total_score'] for a in analyses) / total_symbols
        
        print(f"   Símbolos analizados: {total_symbols}")
        print(f"   Oportunidades encontradas: {passing_symbols}")
        print(f"   Tasa de éxito: {pass_rate:.1f}%")
        print(f"   Movimiento promedio: {avg_movement:+.2f}%")
        print(f"   Volumen promedio: {avg_volume:.2f}x")
        print(f"   Score promedio: {avg_score:.3f}")
        
        # Rate limit status
        rate_status = data_provider.get_rate_limit_status()
        print(f"\n   🔧 Rate Limit:")
        print(f"      Requests: {rate_status['current_requests']}/{rate_status['max_requests']}")
        print(f"      Restantes: {rate_status['remaining_requests']}")
        print(f"      Reset en: {rate_status['time_to_reset']:.0f} segundos")
    
    # 9. Limpiar
    print("\n9. 🧹 Limpiando recursos...")
    data_provider.cleanup()
    telegram_bot.cleanup()
    
    print("   ✅ Recursos limpiados")
    
    # 10. Guardar resultados
    print("\n10. 💾 Guardando resultados...")
    
    results_file = "data/test_results.json"
    os.makedirs("data", exist_ok=True)
    
    results_data = {
        "timestamp": datetime.now().isoformat(),
        "total_symbols": len(analyses),
        "opportunities_found": len(top_opportunities),
        "opportunities": [
            {
                "symbol": opp['symbol'],
                "movement_percent": opp['indicators']['movement_percent'],
                "relative_volume": opp['indicators']['relative_volume'],
                "atr_percent": opp['indicators']['atr_percent'],
                "probability_percent": opp['indicators']['probability_percent'],
                "score": opp['indicators']['total_score'],
                "prices": opp['prices']
            }
            for opp in top_opportunities
        ],
        "metrics": {
            "pass_rate_percent": pass_rate if analyses else 0,
            "avg_movement_percent": avg_movement if analyses else 0,
            "avg_relative_volume": avg_volume if analyses else 0,
            "avg_score": avg_score if analyses else 0
        }
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Resultados guardados en {results_file}")
    
    print("\n" + "=" * 60)
    print("🎉 Prueba completada exitosamente!")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)