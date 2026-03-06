import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from utils.logger import logger


class MarketAnalyzer:
    """
    Analizador de mercado para BMV.
    
    Responsabilidades:
    1. Calcular indicadores técnicos (ATR, volumen relativo, etc.)
    2. Evaluar criterios de filtrado
    3. Calcular probabilidad de movimiento
    4. Ordenar oportunidades
    """
    
    def __init__(
        self,
        min_movement_percent: float = 2.0,
        min_relative_volume: float = 1.8,
        min_atr_percent: float = 2.5,
        min_price_mxn: float = 10.0
    ):
        """
        Args:
            min_movement_percent: Movimiento mínimo porcentual
            min_relative_volume: Volumen relativo mínimo
            min_atr_percent: ATR mínimo como porcentaje del precio
            min_price_mxn: Precio mínimo en MXN
        """
        self.min_movement_percent = min_movement_percent
        self.min_relative_volume = min_relative_volume
        self.min_atr_percent = min_atr_percent
        self.min_price_mxn = min_price_mxn
        
        logger.info(f"MarketAnalyzer inicializado. Criterios: movimiento>{min_movement_percent}%, volumen>{min_relative_volume}x, ATR>{min_atr_percent}%")
    
    def calculate_indicators(self, quote_data: Dict, historical_data: Optional[List] = None) -> Dict:
        """
        Calcula indicadores técnicos para un símbolo.
        
        Args:
            quote_data: Datos de quote actuales
            historical_data: Datos históricos para cálculos (opcional)
            
        Returns:
            Dict con indicadores calculados
        """
        indicators = {}
        
        try:
            # Extraer datos básicos
            current_price = quote_data.get('p')  # Precio actual
            last_price = quote_data.get('ld')    # Último precio negociado
            open_price = quote_data.get('o')     # Precio de apertura
            high_price = quote_data.get('h')     # Máximo del día
            low_price = quote_data.get('l')      # Mínimo del día
            volume = quote_data.get('v', 0)      # Volumen del día
            change_percent = quote_data.get('chp', 0)  # Cambio porcentual
            
            # 1. Movimiento porcentual
            if last_price and open_price and open_price > 0:
                daily_movement = ((current_price or last_price) - open_price) / open_price * 100
            else:
                daily_movement = change_percent if change_percent else 0
            
            indicators['movement_percent'] = daily_movement
            indicators['movement_absolute'] = abs(daily_movement)
            indicators['direction'] = 'alcista' if daily_movement > 0 else 'bajista' if daily_movement < 0 else 'neutral'
            
            # 2. Volumen relativo (simplificado - en producción usaríamos histórico)
            # Por ahora, usamos un valor estimado basado en el precio
            if volume > 0 and current_price:
                # Estimación muy simplificada - en producción usaríamos promedio histórico
                estimated_avg_volume = 1000000  # 1M de volumen promedio estimado
                relative_volume = volume / estimated_avg_volume
            else:
                relative_volume = 1.0
            
            indicators['relative_volume'] = relative_volume
            indicators['volume_score'] = min(relative_volume / 3.0, 1.0)  # Normalizado a 0-1
            
            # 3. ATR (Average True Range) - simplificado
            if all([high_price, low_price, current_price]):
                # True Range simplificado para un solo día
                tr1 = abs(high_price - low_price)
                tr2 = abs(high_price - (last_price or current_price))
                tr3 = abs(low_price - (last_price or current_price))
                true_range = max(tr1, tr2, tr3)
                
                atr_percent = (true_range / current_price) * 100 if current_price > 0 else 0
            else:
                atr_percent = 0
            
            indicators['atr_percent'] = atr_percent
            indicators['atr_score'] = min(atr_percent / 5.0, 1.0)  # Normalizado a 0-1
            
            # 4. Momentum score
            momentum_score = 0.0
            if daily_movement > 0:
                momentum_score = min(daily_movement / 5.0, 1.0)  # Normalizado a 0-1
            elif daily_movement < 0:
                momentum_score = -min(abs(daily_movement) / 5.0, 1.0)
            
            indicators['momentum_score'] = momentum_score
            
            # 5. Liquidity score (basado en volumen y precio)
            if volume > 0 and current_price:
                liquidity = volume * current_price  # Valor transado aproximado
                liquidity_score = min(np.log10(liquidity) / 9.0, 1.0)  # Normalizado a 0-1
            else:
                liquidity_score = 0.5  # Valor por defecto
            
            indicators['liquidity_score'] = liquidity_score
            
            # 6. Score total (probabilidad estimada)
            total_score = (
                indicators['volume_score'] * 0.3 +
                indicators['atr_score'] * 0.2 +
                abs(momentum_score) * 0.3 +
                liquidity_score * 0.2
            )
            
            indicators['total_score'] = total_score
            indicators['probability_percent'] = total_score * 100
            
            logger.debug(f"Indicadores calculados: movimiento={daily_movement:.2f}%, volumen={relative_volume:.2f}x, ATR={atr_percent:.2f}%, score={total_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            # Valores por defecto en caso de error
            indicators = {
                'movement_percent': 0,
                'movement_absolute': 0,
                'direction': 'neutral',
                'relative_volume': 1.0,
                'volume_score': 0.5,
                'atr_percent': 0,
                'atr_score': 0.5,
                'momentum_score': 0,
                'liquidity_score': 0.5,
                'total_score': 0.5,
                'probability_percent': 50.0
            }
        
        return indicators
    
    def evaluate_criteria(self, symbol_data: Dict, indicators: Dict) -> Tuple[bool, Dict]:
        """
        Evalúa si un símbolo cumple con los criterios de filtrado.
        
        Args:
            symbol_data: Datos del símbolo
            indicators: Indicadores calculados
            
        Returns:
            Tuple (cumple_criterios, razones)
        """
        reasons = {}
        passes = True
        
        # 1. Movimiento mínimo
        movement_abs = indicators['movement_absolute']
        if movement_abs < self.min_movement_percent:
            passes = False
            reasons['movement'] = f"Movimiento insuficiente ({movement_abs:.2f}% < {self.min_movement_percent}%)"
        else:
            reasons['movement'] = f"Movimiento adecuado ({movement_abs:.2f}%)"
        
        # 2. Volumen relativo mínimo
        rel_volume = indicators['relative_volume']
        if rel_volume < self.min_relative_volume:
            passes = False
            reasons['volume'] = f"Volumen insuficiente ({rel_volume:.2f}x < {self.min_relative_volume}x)"
        else:
            reasons['volume'] = f"Volumen adecuado ({rel_volume:.2f}x)"
        
        # 3. ATR mínimo
        atr_percent = indicators['atr_percent']
        if atr_percent < self.min_atr_percent:
            passes = False
            reasons['atr'] = f"ATR insuficiente ({atr_percent:.2f}% < {self.min_atr_percent}%)"
        else:
            reasons['atr'] = f"ATR adecuado ({atr_percent:.2f}%)"
        
        # 4. Precio mínimo
        current_price = symbol_data.get('quote', {}).get('p', 0)
        if current_price < self.min_price_mxn:
            passes = False
            reasons['price'] = f"Precio muy bajo (${current_price:.2f} < ${self.min_price_mxn})"
        else:
            reasons['price'] = f"Precio adecuado (${current_price:.2f})"
        
        # 5. Score mínimo (probabilidad)
        probability = indicators['probability_percent']
        min_probability = 60.0  # Probabilidad mínima del 60%
        if probability < min_probability:
            passes = False
            reasons['probability'] = f"Probabilidad baja ({probability:.1f}% < {min_probability}%)"
        else:
            reasons['probability'] = f"Probabilidad adecuada ({probability:.1f}%)"
        
        return passes, reasons
    
    def calculate_entry_exit_prices(self, symbol_data: Dict, indicators: Dict) -> Dict:
        """
        Calcula precios de entrada, objetivo y stop.
        
        Args:
            symbol_data: Datos del símbolo
            indicators: Indicadores calculados
            
        Returns:
            Dict con precios sugeridos
        """
        try:
            quote_data = symbol_data.get('quote', {})
            current_price = quote_data.get('p') or quote_data.get('ld', 0)
            direction = indicators['direction']
            movement = indicators['movement_percent']
            atr_percent = indicators['atr_percent']
            
            if current_price <= 0:
                return {
                    'entry': 0,
                    'target': 0,
                    'stop': 0,
                    'risk_reward': 0
                }
            
            # Basado en la dirección del movimiento
            if direction == 'alcista' and movement > 0:
                # Para movimientos alcistas
                entry_price = current_price * 0.995  # Entrar ligeramente por debajo
                target_price = current_price * (1 + max(0.03, min(0.06, movement/100 * 1.5)))  # Objetivo 3-6%
                stop_price = current_price * 0.98  # Stop al 2% por debajo
            elif direction == 'bajista' and movement < 0:
                # Para movimientos bajistas (short)
                entry_price = current_price * 1.005  # Entrar ligeramente por encima
                target_price = current_price * (1 - max(0.03, min(0.06, abs(movement)/100 * 1.5)))  # Objetivo 3-6%
                stop_price = current_price * 1.02  # Stop al 2% por encima
            else:
                # Movimiento neutral o muy pequeño
                entry_price = current_price
                target_price = current_price
                stop_price = current_price * 0.99  # Stop conservador
            
            # Ajustar basado en ATR
            atr_value = current_price * (atr_percent / 100)
            if atr_value > 0:
                # Usar ATR para ajustar stop y target
                if direction == 'alcista':
                    stop_price = max(stop_price, current_price - (atr_value * 1.5))
                    target_price = min(target_price, current_price + (atr_value * 2.0))
                elif direction == 'bajista':
                    stop_price = min(stop_price, current_price + (atr_value * 1.5))
                    target_price = max(target_price, current_price - (atr_value * 2.0))
            
            # Calcular relación riesgo/recompensa
            if direction == 'alcista':
                risk = entry_price - stop_price
                reward = target_price - entry_price
            elif direction == 'bajista':
                risk = stop_price - entry_price
                reward = entry_price - target_price
            else:
                risk = reward = 0
            
            risk_reward = reward / risk if risk > 0 else 0
            
            return {
                'entry': round(entry_price, 2),
                'target': round(target_price, 2),
                'stop': round(stop_price, 2),
                'risk_reward': round(risk_reward, 2),
                'risk_percent': round(abs((stop_price - entry_price) / entry_price * 100), 2) if entry_price > 0 else 0,
                'reward_percent': round(abs((target_price - entry_price) / entry_price * 100), 2) if entry_price > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculando precios: {e}")
            return {
                'entry': 0,
                'target': 0,
                'stop': 0,
                'risk_reward': 0,
                'risk_percent': 0,
                'reward_percent': 0
            }
    
    def analyze_symbol(self, symbol_data: Dict) -> Optional[Dict]:
        """
        Analiza un símbolo completo.
        
        Args:
            symbol_data: Datos del símbolo (debe incluir 'symbol' y 'quote')
            
        Returns:
            Dict con análisis completo o None si hay error
        """
        try:
            symbol_info = symbol_data.get('symbol', {})
            quote_data = symbol_data.get('quote', {})
            
            if not symbol_info or not quote_data:
                logger.warning(f"Datos incompletos para análisis")
                return None
            
            symbol_code = symbol_info.get('code', 'UNKNOWN')
            
            # Calcular indicadores
            indicators = self.calculate_indicators(quote_data)
            
            # Evaluar criterios
            passes_criteria, reasons = self.evaluate_criteria(symbol_data, indicators)
            
            # Calcular precios de entrada/salida
            prices = self.calculate_entry_exit_prices(symbol_data, indicators)
            
            # Crear análisis completo
            analysis = {
                'symbol': symbol_code,
                'symbol_info': symbol_info,
                'quote': quote_data,
                'indicators': indicators,
                'passes_criteria': passes_criteria,
                'reasons': reasons,
                'prices': prices,
                'analysis_time': datetime.now().isoformat()
            }
            
            logger.debug(f"Análisis completado para {symbol_code}: pasa={passes_criteria}, score={indicators['total_score']:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando símbolo: {e}")
            return None
    
    def filter_and_rank_opportunities(self, analyses: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        Filtra y ordena oportunidades.
        
        Args:
            analyses: Lista de análisis de símbolos
            top_n: Número máximo de oportunidades a retornar
            
        Returns:
            Lista de oportunidades ordenadas por score
        """
        # Filtrar solo los que pasan los criterios
        filtered = [analysis for analysis in analyses if analysis.get('passes_criteria', False)]
        
        # Ordenar por score total (descendente)
        filtered.sort(key=lambda x: x.get('indicators', {}).get('total_score', 0), reverse=True)
        
        # Tomar top N
        top_opportunities = filtered[:top_n]
        
        logger.info(f"Filtradas {len(top_opportunities)} oportunidades de {len(analyses)} análisis")
        
        return top_opportunities