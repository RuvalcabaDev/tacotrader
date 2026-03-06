import time
import schedule
import threading
from typing import Optional, Callable
from datetime import datetime, timedelta

from utils.logger import logger
from scheduler.market_hours import MarketHoursChecker


class TaskScheduler:
    """
    Scheduler para tareas de TacoTrader.
    
    Responsabilidades:
    1. Programar ejecución del screener durante horario de mercado
    2. Manejar pausas fuera de horario
    3. Ejecutar tareas de mantenimiento
    4. Monitorear estado del sistema
    """
    
    def __init__(
        self,
        market_hours_checker: MarketHoursChecker,
        check_interval_minutes: int = 10
    ):
        """
        Args:
            market_hours_checker: Verificador de horarios de mercado
            check_interval_minutes: Intervalo de check durante horario de mercado
        """
        self.market_hours = market_hours_checker
        self.check_interval = check_interval_minutes
        
        # Callbacks
        self.screener_callback: Optional[Callable] = None
        self.maintenance_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        
        # Estado
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0
        
        # Configurar schedule
        self._setup_schedule()
        
        logger.info(f"TaskScheduler inicializado. Intervalo: {check_interval_minutes} minutos")
    
    def _setup_schedule(self) -> None:
        """Configura las tareas programadas."""
        # Limpiar schedule existente
        schedule.clear()
        
        # Tarea principal: ejecutar screener durante horario de mercado
        schedule.every(self.check_interval).minutes.do(
            self._run_screener_if_market_open
        ).tag('screener')
        
        # Tarea de mantenimiento: cada hora
        schedule.every().hour.do(
            self._run_maintenance
        ).tag('maintenance')
        
        # Tarea de status: cada 30 minutos
        schedule.every(30).minutes.do(
            self._run_status_check
        ).tag('status')
        
        logger.debug("Schedule configurado")
    
    def set_screener_callback(self, callback: Callable) -> None:
        """
        Establece callback para el screener.
        
        Args:
            callback: Función a ejecutar cuando se active el screener
        """
        self.screener_callback = callback
        logger.debug("Callback de screener establecido")
    
    def set_maintenance_callback(self, callback: Callable) -> None:
        """
        Establece callback para mantenimiento.
        
        Args:
            callback: Función a ejecutar para mantenimiento
        """
        self.maintenance_callback = callback
        logger.debug("Callback de mantenimiento establecido")
    
    def set_status_callback(self, callback: Callable) -> None:
        """
        Establece callback para status.
        
        Args:
            callback: Función a ejecutar para status
        """
        self.status_callback = callback
        logger.debug("Callback de status establecido")
    
    def _run_screener_if_market_open(self) -> None:
        """Ejecuta el screener solo si el mercado está abierto."""
        try:
            if self.market_hours.is_market_open():
                logger.info("Ejecutando screener (mercado abierto)")
                
                if self.screener_callback:
                    self.screener_callback()
                else:
                    logger.warning("No hay callback de screener configurado")
                
                self.last_run = datetime.now()
                self.run_count += 1
                
                # Log rate limit status
                self._log_rate_limit_status()
            else:
                logger.debug("Mercado cerrado. Saltando screener.")
                
        except Exception as e:
            logger.error(f"Error ejecutando screener: {e}")
            self.error_count += 1
    
    def _run_maintenance(self) -> None:
        """Ejecuta tareas de mantenimiento."""
        try:
            logger.debug("Ejecutando tareas de mantenimiento")
            
            if self.maintenance_callback:
                self.maintenance_callback()
            else:
                logger.debug("No hay callback de mantenimiento configurado")
                
        except Exception as e:
            logger.error(f"Error en mantenimiento: {e}")
    
    def _run_status_check(self) -> None:
        """Ejecuta check de status."""
        try:
            logger.debug("Ejecutando check de status")
            
            if self.status_callback:
                self.status_callback()
            else:
                # Status por defecto
                status = self.get_status()
                logger.info(f"Status: {status}")
                
        except Exception as e:
            logger.error(f"Error en check de status: {e}")
    
    def _log_rate_limit_status(self) -> None:
        """Registra estado del rate limiting."""
        # Esto sería implementado cuando tengamos el data provider
        pass
    
    def _scheduler_loop(self) -> None:
        """Loop principal del scheduler."""
        logger.info("Iniciando loop del scheduler")
        
        while self.running:
            try:
                # Ejecutar tareas pendientes
                schedule.run_pending()
                
                # Calcular tiempo hasta próxima ejecución
                next_run = schedule.next_run()
                if next_run:
                    wait_seconds = (next_run - datetime.now()).total_seconds()
                    wait_seconds = max(1, min(wait_seconds, 60))  # Limitar entre 1 y 60 segundos
                else:
                    wait_seconds = 30
                
                # Esperar hasta próxima ejecución
                time.sleep(wait_seconds)
                
            except KeyboardInterrupt:
                logger.info("Scheduler interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"Error en scheduler loop: {e}")
                time.sleep(30)  # Esperar antes de reintentar
        
        logger.info("Loop del scheduler finalizado")
    
    def start(self) -> None:
        """Inicia el scheduler en un thread separado."""
        if self.running:
            logger.warning("Scheduler ya está ejecutándose")
            return
        
        self.running = True
        
        # Crear y empezar thread
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("Scheduler iniciado")
    
    def stop(self) -> None:
        """Detiene el scheduler."""
        if not self.running:
            logger.warning("Scheduler no está ejecutándose")
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("Scheduler detenido")
    
    def run_once(self) -> None:
        """Ejecuta el screener una vez (para testing)."""
        logger.info("Ejecutando screener una vez (manual)")
        self._run_screener_if_market_open()
    
    def get_status(self) -> dict:
        """
        Obtiene el estado del scheduler.
        
        Returns:
            Dict con información del estado
        """
        market_status = self.market_hours.get_market_status()
        
        status = {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "check_interval_minutes": self.check_interval,
            "market_status": market_status,
            "next_screener_run": schedule.next_run().isoformat() if schedule.next_run() else None,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }
        
        # Calcular tiempo desde última ejecución
        if self.last_run:
            time_since_last = datetime.now() - self.last_run
            status["time_since_last_run_minutes"] = int(time_since_last.total_seconds() / 60)
        
        return status
    
    def adjust_interval_based_on_market(self) -> None:
        """
        Ajusta el intervalo basado en el estado del mercado.
        
        Fuera de horario: intervalos más largos
        Dentro de horario: intervalos normales
        """
        if self.market_hours.is_market_open():
            # Durante horario de mercado: intervalo normal
            new_interval = self.check_interval
        else:
            # Fuera de horario: intervalo más largo
            next_open = self.market_hours.get_next_open_time()
            if next_open:
                time_to_open = (next_open - datetime.now()).total_seconds()
                
                if time_to_open < 3600:  # Menos de 1 hora
                    new_interval = 30  # 30 minutos
                elif time_to_open < 6 * 3600:  # Menos de 6 horas
                    new_interval = 60  # 1 hora
                else:
                    new_interval = 240  # 4 horas
            else:
                new_interval = 60  # 1 hora por defecto
        
        # Actualizar schedule si el intervalo cambió
        if new_interval != self.check_interval:
            old_interval = self.check_interval
            self.check_interval = new_interval
            self._setup_schedule()
            
            logger.info(f"Intervalo ajustado: {old_interval} -> {new_interval} minutos")
    
    def cleanup(self):
        """Limpia recursos del scheduler."""
        self.stop()
        schedule.clear()
        logger.debug("Scheduler limpiado")