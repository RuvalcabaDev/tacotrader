import telebot
from typing import Dict, List, Optional, Any
from datetime import datetime

from utils.logger import logger


class TelegramAlertBot:
    """
    Bot de Telegram para enviar alertas de trading.
    
    Usa pyTelegramBotAPI 4.31.0
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Args:
            bot_token: Token del bot de Telegram
            chat_id: ID del chat/canal donde enviar alertas
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        # Inicializar bot
        self.bot = telebot.TeleBot(bot_token)
        
        # Cache de alertas enviadas (para evitar duplicados)
        self.sent_alerts = {}
        
        logger.info(f"TelegramAlertBot inicializado. Chat ID: {chat_id}")
    
    def _format_bmv_alert(self, analysis: Dict) -> str:
        """
        Formatea una alerta BMV según el template especificado.
        
        Args:
            analysis: Análisis completo del símbolo
            
        Returns:
            Mensaje formateado para Telegram
        """
        try:
            symbol = analysis['symbol']
            symbol_info = analysis['symbol_info']
            quote = analysis['quote']
            indicators = analysis['indicators']
            prices = analysis['prices']
            reasons = analysis['reasons']
            
            # Extraer datos
            current_price = quote.get('p') or quote.get('ld', 0)
            movement = indicators['movement_percent']
            rel_volume = indicators['relative_volume']
            atr_percent = indicators['atr_percent']
            direction = indicators['direction']
            probability = indicators['probability_percent']
            
            # Capitalización estimada
            market_cap = symbol_info.get('estimated_cap_mxn_b', 0)
            
            # Formatear mensaje
            message = f"🚨 BMV ALERT\n\n"
            message += f"Ticker: {symbol}\n"
            message += f"Movimiento: {movement:+.2f}%\n"
            message += f"Volumen relativo: {rel_volume:.1f}x\n"
            message += f"Precio actual: ${current_price:.2f}\n\n"
            
            message += f"ATR: {atr_percent:.2f}%\n"
            message += f"Capitalización: ${market_cap:.1f}B MXN\n\n"
            
            message += f"Momentum: {direction.capitalize()}\n"
            message += f"Entrada sugerida: ${prices['entry']:.2f}\n"
            message += f"Objetivo: ${prices['target']:.2f}\n"
            message += f"Stop: ${prices['stop']:.2f}\n\n"
            
            message += f"Riesgo/Recompensa: {prices['risk_reward']:.2f}\n"
            message += f"Probabilidad estimada: {probability:.1f}%\n\n"
            
            # Agregar razones del filtrado
            message += "📊 Criterios:\n"
            for criterion, reason in reasons.items():
                message += f"• {reason}\n"
            
            # Timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"\n🕒 {timestamp}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formateando alerta: {e}")
            return f"🚨 Error formateando alerta para {analysis.get('symbol', 'UNKNOWN')}"
    
    def _should_send_alert(self, symbol: str, analysis: Dict) -> bool:
        """
        Determina si se debe enviar una alerta (evitar duplicados).
        
        Args:
            symbol: Código del símbolo
            analysis: Análisis del símbolo
            
        Returns:
            True si se debe enviar, False si no
        """
        # Verificar si ya enviamos una alerta para este símbolo hoy
        today = datetime.now().strftime("%Y-%m-%d")
        alert_key = f"{symbol}_{today}"
        
        if alert_key in self.sent_alerts:
            last_alert_time = self.sent_alerts[alert_key]
            time_since_last = datetime.now() - last_alert_time
            
            # No enviar más de una alerta por símbolo cada 4 horas
            if time_since_last.total_seconds() < 4 * 3600:
                logger.debug(f"Alerta reciente para {symbol}. Saltando...")
                return False
        
        return True
    
    def send_alert(self, analysis: Dict) -> bool:
        """
        Envía una alerta a Telegram.
        
        Args:
            analysis: Análisis completo del símbolo
            
        Returns:
            True si se envió exitosamente, False si no
        """
        try:
            symbol = analysis['symbol']
            
            # Verificar si debemos enviar la alerta
            if not self._should_send_alert(symbol, analysis):
                return False
            
            # Formatear mensaje
            message = self._format_bmv_alert(analysis)
            
            # Enviar mensaje
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Registrar alerta enviada
            today = datetime.now().strftime("%Y-%m-%d")
            alert_key = f"{symbol}_{today}"
            self.sent_alerts[alert_key] = datetime.now()
            
            logger.info(f"Alerta enviada para {symbol} a Telegram")
            return True
            
        except telebot.apihelper.ApiTelegramException as e:
            logger.error(f"Error de API de Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Error enviando alerta a Telegram: {e}")
            return False
    
    def send_batch_alerts(self, analyses: List[Dict]) -> Dict[str, bool]:
        """
        Envía múltiples alertas.
        
        Args:
            analyses: Lista de análisis
            
        Returns:
            Dict con resultados por símbolo
        """
        results = {}
        
        for analysis in analyses:
            symbol = analysis['symbol']
            success = self.send_alert(analysis)
            results[symbol] = success
            
            # Pequeña pausa entre alertas
            import time
            time.sleep(0.5)
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Alertas enviadas: {successful} exitosas de {len(results)}")
        
        return results
    
    def send_status_message(self, message: str) -> bool:
        """
        Envía un mensaje de estado/error a Telegram.
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            True si se envió exitosamente, False si no
        """
        try:
            formatted_message = f"📊 TacoTrader Status\n\n{message}"
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted_message,
                parse_mode='HTML'
            )
            
            logger.info(f"Mensaje de estado enviado a Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando mensaje de estado: {e}")
            return False
    
    def send_error_message(self, error: str, context: str = "") -> bool:
        """
        Envía un mensaje de error a Telegram.
        
        Args:
            error: Descripción del error
            context: Contexto adicional
            
        Returns:
            True si se envió exitosamente, False si no
        """
        try:
            message = f"❌ TacoTrader Error\n\n"
            message += f"Error: {error}\n"
            if context:
                message += f"Contexto: {context}\n"
            message += f"\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Mensaje de error enviado a Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando mensaje de error: {e}")
            return False
    
    def cleanup(self):
        """Limpia recursos del bot."""
        # Limpiar cache viejo (más de 7 días)
        cutoff_time = datetime.now().timestamp() - (7 * 24 * 3600)
        
        old_keys = []
        for key, alert_time in self.sent_alerts.items():
            if alert_time.timestamp() < cutoff_time:
                old_keys.append(key)
        
        for key in old_keys:
            self.sent_alerts.pop(key, None)
        
        logger.debug(f"Cache de alertas limpiado. Eliminadas {len(old_keys)} entradas")