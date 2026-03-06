import time
import threading
from typing import Optional
from datetime import datetime, timedelta
from utils.logger import logger


class RateLimiter:
    """
    Rate limiter para controlar peticiones a la API.
    
    Capa gratuita de iTick: 5 peticiones por minuto.
    """
    
    def __init__(self, max_requests: int = 5, period_seconds: int = 60):
        """
        Args:
            max_requests: Máximo número de peticiones en el período
            period_seconds: Período en segundos
        """
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.requests = []
        self.lock = threading.Lock()
        
        logger.info(f"Rate limiter configurado: {max_requests} requests por {period_seconds} segundos")
    
    def _clean_old_requests(self) -> None:
        """Elimina peticiones fuera del período actual."""
        now = time.time()
        cutoff = now - self.period_seconds
        
        with self.lock:
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
    
    def can_make_request(self) -> bool:
        """
        Verifica si se puede hacer una petición.
        
        Returns:
            True si se puede hacer la petición, False si hay que esperar
        """
        self._clean_old_requests()
        
        with self.lock:
            return len(self.requests) < self.max_requests
    
    def wait_if_needed(self) -> None:
        """Espera si es necesario para respetar el rate limit."""
        while not self.can_make_request():
            self._clean_old_requests()
            
            with self.lock:
                if self.requests:
                    # Calcular cuándo se liberará el siguiente slot
                    oldest_request = min(self.requests)
                    next_available = oldest_request + self.period_seconds
                    wait_time = max(0, next_available - time.time())
                    
                    if wait_time > 0:
                        logger.debug(f"Rate limit alcanzado. Esperando {wait_time:.1f} segundos")
                        time.sleep(wait_time)
            
            self._clean_old_requests()
    
    def record_request(self) -> None:
        """Registra una petición realizada."""
        with self.lock:
            self.requests.append(time.time())
    
    def get_remaining_requests(self) -> int:
        """
        Obtiene el número de peticiones restantes en el período actual.
        
        Returns:
            Número de peticiones que se pueden hacer antes de esperar
        """
        self._clean_old_requests()
        
        with self.lock:
            return max(0, self.max_requests - len(self.requests))
    
    def get_time_to_next_reset(self) -> float:
        """
        Obtiene el tiempo hasta el próximo reset del rate limit.
        
        Returns:
            Segundos hasta que se reinicie el contador
        """
        self._clean_old_requests()
        
        with self.lock:
            if not self.requests:
                return 0
            
            oldest_request = min(self.requests)
            reset_time = oldest_request + self.period_seconds
            return max(0, reset_time - time.time())
    
    def get_status(self) -> dict:
        """
        Obtiene el estado actual del rate limiter.
        
        Returns:
            Dict con información del estado
        """
        return {
            "max_requests": self.max_requests,
            "period_seconds": self.period_seconds,
            "current_requests": len(self.requests),
            "remaining_requests": self.get_remaining_requests(),
            "time_to_reset": self.get_time_to_next_reset(),
            "requests_per_minute": len(self.requests) / (self.period_seconds / 60)
        }


# Rate limiter global para la API de iTick
# 5 requests por minuto en capa gratuita
itick_rate_limiter = RateLimiter(max_requests=5, period_seconds=60)