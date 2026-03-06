import time
import sys
from typing import Dict, List, Optional
from datetime import datetime

from config.loader import config_loader
from data.itick_provider import ITickProvider
from data.symbol_manager import SymbolManager
from screener.analyzer import MarketAnalyzer
from alerts.telegram_bot import TelegramAlertBot
from scheduler.market_hours import MarketHoursChecker
from scheduler.task_scheduler import TaskScheduler
from utils.logger import logger


class TacoTraderBMV:
    """
    Clase principal de TacoTrader para el mercado BMV.
    
    Orquesta todos los componentes:
    1. Data providers (iTick)
    2. Symbol management
    3. Market analysis
    4. Alert system
    5. Task scheduling
    """
    
    def __init__(self):
        """Inicializa TacoTrader BMV."""
        logger.info("=" * 60)
        logger.info("🌮 Inicializando TacoTrader BMV")
        logger.info("=" * 60)
        
        # Cargar configuración
        self.config = config_loader
        
        # Inicializar componentes
        self._init_components()
        
        # Estado
        self.running = False
        self.start_time = None
        self.error_count = 0
        self.last_error = None
        self.last_successful_run = None
        self.health_status = "initializing"
        
        self.health_status = "healthy"
        logger.info("TacoTrader BMV inicializado exitosamente")
    
    def _init_components(self) -> None:
        """Inicializa todos los componentes."""
        # 1. Data Provider (iTick)
        itick_config = self.config.get_itick_config()
        self.data_provider = ITickProvider(
            api_key=itick_config['api_key'],
            base_url=itick_config['base_url'],
            use_websocket=True,  # Habilitar WebSocket para datos en tiempo real
            max_symbols=self.config.get('BMV_MAX_SYMBOLS', 100)
        )
        
        # 2. Symbol Manager
        self.symbol_manager = SymbolManager(
            data_provider=self.data_provider,
            data_dir="data",
            max_symbols=self.config.get('BMV_MAX_SYMBOLS', 100),
            refresh_hours=24
        )
        
        # 3. Market Analyzer
        screener_config = self.config.get_screener_config()
        criteria = screener_config.get('criteria', {})
        
        self.analyzer = MarketAnalyzer(
            min_movement_percent=criteria.get('min_movement_percent', 2.0),
            min_relative_volume=criteria.get('min_relative_volume', 1.8),
            min_atr_percent=criteria.get('min_atr_percent', 2.5),
            min_price_mxn=criteria.get('min_price_mxn', 10.0)
        )
        
        # 4. Telegram Bot
        telegram_config = self.config.get_telegram_config()
        self.telegram_bot = TelegramAlertBot(
            bot_token=telegram_config['bot_token'],
            chat_id=telegram_config['chat_id']
        )
        
        # 5. Market Hours Checker
        market_config = self.config.get_market_config()
        self.market_hours = MarketHoursChecker(
            market_timezone=market_config.get('timezone', 'America/Mexico_City'),
            open_time=market_config.get('open_time', '07:00'),
            close_time=market_config.get('close_time', '15:00')
        )
        
        # 6. Task Scheduler
        self.scheduler = TaskScheduler(
            market_hours_checker=self.market_hours,
            check_interval_minutes=market_config.get('check_interval_minutes', 10)
        )
        
        # Configurar callbacks
        self.scheduler.set_screener_callback(self.run_screener)
        self.scheduler.set_maintenance_callback(self.run_maintenance)
        self.scheduler.set_status_callback(self.send_status_update)
        
        # Suscribir símbolos al WebSocket cuando el mercado abra
        self._setup_websocket_subscription()
        
        logger.debug("Todos los componentes inicializados")
    
    def run_screener(self) -> None:
        """
        Ejecuta el screener completo.
        
        1. Obtiene símbolos
        2. Obtiene quotes
        3. Analiza cada símbolo
        4. Filtra oportunidades
        5. Envía alertas
        """
        logger.info("🚀 Ejecutando screener BMV")
        
        try:
            # 1. Obtener símbolos
            symbols = self.symbol_manager.get_symbols()
            symbol_codes = [s['code'] for s in symbols]
            
            if not symbol_codes:
                logger.error("No se pudieron obtener símbolos")
                return
            
            logger.info(f"Analizando {len(symbol_codes)} símbolos")
            
            # 2. Obtener quotes (con rate limiting)
            quotes = self.data_provider.get_batch_quotes(symbol_codes)
            
            # 3. Analizar cada símbolo
            analyses = []
            valid_symbols = 0
            
            for symbol_code, quote in quotes.items():
                if quote is None:
                    continue
                
                symbol_info = self.symbol_manager.get_symbol_info(symbol_code)
                if not symbol_info:
                    continue
                
                symbol_data = {
                    'symbol': symbol_info,
                    'quote': quote
                }
                
                analysis = self.analyzer.analyze_symbol(symbol_data)
                if analysis:
                    analyses.append(analysis)
                    valid_symbols += 1
            
            logger.info(f"Analizados {valid_symbols} símbolos válidos de {len(symbol_codes)}")
            
            # 4. Filtrar y ordenar oportunidades
            top_opportunities = self.analyzer.filter_and_rank_opportunities(
                analyses,
                top_n=self.config.get_screener_config().get('top_results', 5)
            )
            
            # 5. Enviar alertas
            if top_opportunities:
                logger.info(f"Enviando {len(top_opportunities)} alertas")
                results = self.telegram_bot.send_batch_alerts(top_opportunities)
                
                # Log resultados
                successful = sum(1 for success in results.values() if success)
                logger.info(f"Alertas enviadas: {successful} exitosas de {len(results)}")
            else:
                logger.info("No se encontraron oportunidades que cumplan los criterios")
            
            # 6. Registrar métricas
            self._log_screener_metrics(analyses, top_opportunities)
            
            # 7. Registrar éxito
            self._record_success()
            
        except Exception as e:
            logger.error(f"Error en screener: {e}")
            self._record_error(e)
            self.telegram_bot.send_error_message(str(e), "run_screener")
    
    def _log_screener_metrics(self, analyses: List[Dict], opportunities: List[Dict]) -> None:
        """Registra métricas del screener."""
        if not analyses:
            return
        
        # Calcular métricas
        total_symbols = len(analyses)
        passing_symbols = len(opportunities)
        pass_rate = (passing_symbols / total_symbols * 100) if total_symbols > 0 else 0
        
        # Calcular promedios
        avg_movement = sum(a['indicators']['movement_percent'] for a in analyses) / total_symbols
        avg_volume = sum(a['indicators']['relative_volume'] for a in analyses) / total_symbols
        avg_score = sum(a['indicators']['total_score'] for a in analyses) / total_symbols
        
        metrics = {
            'total_symbols': total_symbols,
            'passing_symbols': passing_symbols,
            'pass_rate_percent': round(pass_rate, 1),
            'avg_movement_percent': round(avg_movement, 2),
            'avg_relative_volume': round(avg_volume, 2),
            'avg_score': round(avg_score, 3),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Métricas screener: {metrics}")
        
        # Enviar status si hay oportunidades
        if opportunities and pass_rate > 0:
            status_msg = (
                f"📊 Screener completado\n"
                f"Símbolos analizados: {total_symbols}\n"
                f"Oportunidades encontradas: {passing_symbols}\n"
                f"Tasa de éxito: {pass_rate:.1f}%\n"
                f"Movimiento promedio: {avg_movement:+.2f}%\n"
                f"Mejor oportunidad: {opportunities[0]['symbol']} "
                f"(score: {opportunities[0]['indicators']['total_score']:.2f})"
            )
            self.telegram_bot.send_status_message(status_msg)
    
    def run_maintenance(self) -> None:
        """Ejecuta tareas de mantenimiento."""
        logger.info("🛠️ Ejecutando mantenimiento")
        
        try:
            # 1. Limpiar caches
            self.data_provider.cleanup()
            self.telegram_bot.cleanup()
            
            # 2. Actualizar símbolos si es necesario
            self.symbol_manager.get_symbols(force_refresh=False)
            
            # 3. Verificar rate limit status
            rate_limit_status = self.data_provider.get_rate_limit_status()
            logger.info(f"Rate limit status: {rate_limit_status}")
            
            # 4. Ajustar intervalo del scheduler si es necesario
            self.scheduler.adjust_interval_based_on_market()
            
            # 5. Enviar status de mantenimiento
            uptime = datetime.now() - self.start_time if self.start_time else None
            status_msg = (
                f"🛠️ Mantenimiento completado\n"
                f"Uptime: {str(uptime).split('.')[0] if uptime else 'N/A'}\n"
                f"Rate limit: {rate_limit_status.get('remaining_requests', 0)}/{rate_limit_status.get('max_requests', 5)} requests\n"
                f"Próximo reset: {rate_limit_status.get('time_to_reset', 0):.0f}s"
            )
            self.telegram_bot.send_status_message(status_msg)
            
        except Exception as e:
            logger.error(f"Error en mantenimiento: {e}")
    
    def send_status_update(self) -> None:
        """Envía actualización de status."""
        try:
            # Obtener status de todos los componentes
            scheduler_status = self.scheduler.get_status()
            symbol_stats = self.symbol_manager.get_stats()
            market_status = self.market_hours.get_market_status()
            rate_limit_status = self.data_provider.get_rate_limit_status()
            websocket_status = self.get_websocket_status()
            
            # Calcular uptime
            uptime = datetime.now() - self.start_time if self.start_time else None
            
            # Determinar estado de datos
            data_source = "🔌 WebSocket" if websocket_status.get('connected') else "📡 REST API"
            data_status = "✅ TIEMPO REAL" if websocket_status.get('connected') else "⏱️  POLLING"
            
            # Formatear mensaje
            status_msg = (
                f"📊 Status TacoTrader BMV\n\n"
                f"🕒 Uptime: {str(uptime).split('.')[0] if uptime else 'N/A'}\n"
                f"📈 Símbolos: {symbol_stats['total_symbols']}\n"
                f"💰 Cap. total: ${symbol_stats['total_cap_estimated_b_mxn']:.1f}B MXN\n"
                f"⚡ Ejecuciones: {scheduler_status['run_count']}\n"
                f"❌ Errores: {scheduler_status['error_count']}\n\n"
                f"🌎 Mercado: {'✅ ABIERTO' if market_status['market_open'] else '❌ CERRADO'}\n"
                f"🕐 Hora: {market_status['current_time']}\n"
                f"⏰ Próximo: {market_status.get('next_open_time', 'N/A')}\n\n"
                f"📡 Fuente datos: {data_source}\n"
                f"⚡ Estado: {data_status}\n"
            )
            
            # Agregar info de WebSocket si está conectado
            if websocket_status.get('connected'):
                if websocket_status.get('rotating_enabled'):
                    rotation_status = websocket_status.get('rotation_status', {})
                    status_msg += (
                        f"🔌 WebSocket Rotating\n"
                        f"📊 Símbolos: {websocket_status.get('total_symbols_monitored', 0)}\n"
                        f"🔄 Grupos: {websocket_status.get('rotation_groups', 0)}\n"
                        f"⚡ Rotaciones: {websocket_status.get('rotation_count', 0)}\n"
                        f"💾 Cache: {websocket_status.get('data_cache_size', 0)} símbolos\n"
                    )
                else:
                    status_msg += (
                        f"🔌 Símbolos suscritos: {websocket_status.get('subscribed_symbols', 0)}\n"
                        f"💾 Cache: {websocket_status.get('data_cache_size', 0)} símbolos\n"
                    )
            
            # Agregar info de rate limit (solo si no estamos usando WebSocket)
            if not websocket_status.get('connected'):
                status_msg += (
                    f"\n🔧 Rate Limit: {rate_limit_status['remaining_requests']}/{rate_limit_status['max_requests']}\n"
                    f"🔄 Reset en: {rate_limit_status['time_to_reset']:.0f}s"
                )
            
            # Enviar mensaje
            self.telegram_bot.send_status_message(status_msg)
            
        except Exception as e:
            logger.error(f"Error enviando status update: {e}")
            self._record_error(e)
    
    def get_health_status(self) -> Dict:
        """Obtiene el estado de salud del sistema."""
        return {
            'status': self.health_status,
            'running': self.running,
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'error_count': self.error_count,
            'last_error': str(self.last_error) if self.last_error else None,
            'last_successful_run': self.last_successful_run.isoformat() if self.last_successful_run else None,
            'components': {
                'data_provider': self.data_provider is not None,
                'symbol_manager': self.symbol_manager is not None,
                'analyzer': self.analyzer is not None,
                'telegram_bot': self.telegram_bot is not None,
                'market_hours': self.market_hours is not None,
                'scheduler': self.scheduler is not None
            }
        }
    
    def _record_error(self, error: Exception) -> None:
        """Registra un error y actualiza el estado de salud."""
        self.error_count += 1
        self.last_error = error
        self.health_status = "degraded"
        logger.error(f"Error registrado: {error}")
        
        # Si hay demasiados errores consecutivos, marcar como unhealthy
        if self.error_count > 10:
            self.health_status = "unhealthy"
            logger.critical(f"Demasiados errores ({self.error_count}), sistema marcado como unhealthy")
            
            # Intentar enviar alerta de error crítico
            try:
                alert_msg = f"🚨 TacoTrader BMV - Error crítico\nErrores: {self.error_count}\nÚltimo error: {error}"
                self.telegram_bot.send_alert_message(alert_msg)
            except:
                pass
    
    def _record_success(self) -> None:
        """Registra una ejecución exitosa."""
        self.last_successful_run = datetime.now()
        if self.health_status == "degraded" and self.error_count == 0:
            self.health_status = "healthy"
            logger.info("Sistema recuperado a estado healthy")
    
    def _setup_websocket_subscription(self):
        """Configura suscripción de símbolos al WebSocket usando rotating subscriptions."""
        try:
            # Obtener top 30 símbolos por capitalización para WebSocket
            top_symbol_codes = self.symbol_manager.get_top_symbols_for_websocket(count=30)
            top_symbol_metadata = self.symbol_manager.get_symbol_metadata_for_websocket(top_symbol_codes)
            
            if top_symbol_codes:
                # Suscribir símbolos al WebSocket con rotating subscriptions
                success = self.data_provider.subscribe_symbols(top_symbol_codes, top_symbol_metadata)
                
                if success:
                    ws_status = self.data_provider.get_websocket_status()
                    
                    if ws_status.get('rotating_enabled'):
                        rotation_status = ws_status.get('rotation_status', {})
                        total_symbols = rotation_status.get('total_symbols', 0)
                        total_groups = rotation_status.get('total_groups', 0)
                        
                        logger.info(f"Rotating subscriptions configurado. "
                                   f"{total_symbols} símbolos en {total_groups} grupos, "
                                   f"rotando cada 15 segundos")
                        
                        # Enviar mensaje de Telegram
                        if ws_status.get('enabled') and ws_status.get('connected'):
                            message = (
                                "🔌 *WebSocket Rotating Subscriptions*\n\n"
                                f"✅ Conectado a iTick WebSocket\n"
                                f"📊 Monitoreando {total_symbols} símbolos\n"
                                f"🔄 {total_groups} grupos, rotando cada 15s\n"
                                f"🎯 Estrategia: Market Cap Weighted\n\n"
                                f"_Sistema listo para trading en tiempo real_"
                            )
                            
                            try:
                                self.telegram_bot.send_status_message(message)
                                logger.info("Mensaje de WebSocket enviado a Telegram")
                            except Exception as e:
                                logger.error(f"Error enviando mensaje a Telegram: {e}")
                    else:
                        logger.info("WebSocket conectado (sin rotating subscriptions)")
                else:
                    logger.warning("No se pudo configurar suscripción WebSocket")
            else:
                logger.warning("No hay símbolos para suscribir al WebSocket")
                
        except Exception as e:
            logger.error(f"Error configurando suscripción WebSocket: {e}")
    
    def get_websocket_status(self) -> Dict:
        """Obtiene el estado del WebSocket."""
        if hasattr(self.data_provider, 'get_websocket_status'):
            return self.data_provider.get_websocket_status()
        return {"enabled": False, "connected": False}
    
    def is_using_realtime_data(self) -> bool:
        """Verifica si está usando datos en tiempo real via WebSocket."""
        ws_status = self.get_websocket_status()
        return ws_status.get('enabled', False) and ws_status.get('connected', False)
    
    def start(self) -> None:
        """Inicia TacoTrader."""
        if self.running:
            logger.warning("TacoTrader ya está ejecutándose")
            return
        
        logger.info("🚀 Iniciando TacoTrader BMV")
        self.running = True
        self.start_time = datetime.now()
        
        # Enviar mensaje de inicio
        startup_msg = (
            f"🌮 TacoTrader BMV INICIADO\n\n"
            f"Versión: 1.0.0\n"
            f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Mercado: BMV\n"
            f"Horario: {self.market_hours.open_time.strftime('%H:%M')}-{self.market_hours.close_time.strftime('%H:%M')} CDMX\n"
            f"Intervalo: {self.scheduler.check_interval} minutos\n\n"
            f"¡Listo para servir oportunidades! 🌮📈"
        )
        self.telegram_bot.send_status_message(startup_msg)
        
        # Iniciar scheduler
        self.scheduler.start()
        
        logger.info("TacoTrader iniciado exitosamente")
    
    def stop(self) -> None:
        """Detiene TacoTrader."""
        if not self.running:
            logger.warning("TacoTrader no está ejecutándose")
            return
        
        logger.info("🛑 Deteniendo TacoTrader BMV")
        self.running = False
        
        # Detener scheduler
        self.scheduler.stop()
        
        # Limpiar recursos
        self.data_provider.cleanup()
        self.telegram_bot.cleanup()
        
        # Enviar mensaje de parada
        if self.start_time:
            uptime = datetime.now() - self.start_time
            stop_msg = (
                f"🛑 TacoTrader BMV DETENIDO\n\n"
                f"Uptime: {str(uptime).split('.')[0]}\n"
                f"Ejecuciones: {self.scheduler.run_count}\n"
                f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"¡Hasta la próxima! 🌮👋"
            )
            self.telegram_bot.send_status_message(stop_msg)
        
        logger.info("TacoTrader detenido exitosamente")
    
    def run_once(self) -> None:
        """Ejecuta el screener una vez (para testing)."""
        logger.info("🔧 Ejecutando screener una vez (modo testing)")
        self.run_screener()
    
    def get_status(self) -> Dict:
        """
        Obtiene el estado completo de TacoTrader.
        
        Returns:
            Dict con información de estado
        """
        return {
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime': str(datetime.now() - self.start_time).split('.')[0] if self.start_time else None,
            'scheduler': self.scheduler.get_status(),
            'symbols': self.symbol_manager.get_stats(),
            'market': self.market_hours.get_market_status(),
            'rate_limit': self.data_provider.get_rate_limit_status()
        }


def main():
    """Función principal de TacoTrader."""
    try:
        # Crear instancia
        tacotrader = TacoTraderBMV()
        
        # Iniciar
        tacotrader.start()
        
        # Mantener el programa ejecutándose
        logger.info("Presiona Ctrl+C para detener...")
        
        while tacotrader.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nInterrupción recibida. Deteniendo...")
                break
        
        # Detener
        tacotrader.stop()
        
        logger.info("TacoTrader finalizado")
        return 0
        
    except Exception as e:
        logger.error(f"Error fatal en TacoTrader: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())