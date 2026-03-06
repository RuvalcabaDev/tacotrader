#!/usr/bin/env python3
"""
🌮 TacoTrader BMV - El bot que no se clava, se sirve.

Bot de trading automatizado para la Bolsa Mexicana de Valores (BMV).
Analiza el mercado en tiempo real, detecta oportunidades y envía alertas a Telegram.

Características:
- Data provider: iTick API (tiempo real)
- Rate limiting: 5 requests/minuto (capa gratuita)
- Screener: Filtra top 100 empresas BMV
- Alertas: Telegram con formato BMV
- Scheduling: Ejecución automática durante horario de mercado
"""

import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.tacotrader import main

if __name__ == "__main__":
    sys.exit(main())
