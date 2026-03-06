#!/usr/bin/env python3
"""
Script para probar el nuevo horario extendido del mercado BMV.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scheduler.market_hours import MarketHoursChecker
from datetime import datetime, time
import pytz


def test_market_hours():
    """Prueba el nuevo horario extendido."""
    print("🌮 Probando horario extendido BMV (7:00 AM - 3:00 PM CDMX)")
    print("=" * 60)
    
    # Crear verificador con nuevo horario
    checker = MarketHoursChecker(
        market_timezone="America/Mexico_City",
        open_time="07:00",
        close_time="15:00"
    )
    
    print(f"✅ MarketHoursChecker inicializado")
    print(f"   Zona horaria: {checker.market_timezone}")
    print(f"   Hora apertura: {checker.open_time}")
    print(f"   Hora cierre: {checker.close_time}")
    
    # Probar diferentes horas
    test_times = [
        ("06:59", False, "Antes de apertura"),
        ("07:00", True, "En apertura"),
        ("10:00", True, "Durante horario"),
        ("14:59", True, "Antes de cierre"),
        ("15:00", False, "En cierre"),
        ("18:00", False, "Después de cierre"),
    ]
    
    print("\n📊 Pruebas de horario:")
    
    for time_str, expected_open, description in test_times:
        # Crear datetime de prueba
        hour, minute = map(int, time_str.split(':'))
        test_datetime = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        test_datetime = checker.market_timezone.localize(test_datetime)
        
        is_open = checker.is_market_open(test_datetime)
        status = "✅" if is_open == expected_open else "❌"
        
        print(f"  {status} {time_str} - {description}: {'ABIERTO' if is_open else 'CERRADO'} (esperado: {'ABIERTO' if expected_open else 'CERRADO'})")
    
    # Probar status completo
    print("\n📋 Status completo del mercado:")
    status = checker.get_market_status()
    
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("🎉 Prueba de horario extendido completada")


if __name__ == "__main__":
    test_market_hours()