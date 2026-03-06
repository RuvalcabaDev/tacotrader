import pytz
from datetime import datetime, time, timedelta
from typing import Optional, Tuple

from utils.logger import logger


class MarketHoursChecker:
    """
    Verificador de horarios del mercado BMV.
    
    Horario BMV extendido: 7:00 AM - 3:00 PM hora CDMX (Ciudad de México)
    """
    
    def __init__(
        self,
        market_timezone: str = "America/Mexico_City",
        open_time: str = "07:00",
        close_time: str = "15:00"
    ):
        """
        Args:
            market_timezone: Zona horaria del mercado
            open_time: Hora de apertura (formato HH:MM)
            close_time: Hora de cierre (formato HH:MM)
        """
        self.market_timezone = pytz.timezone(market_timezone)
        
        # Parsear horas
        self.open_time = self._parse_time(open_time)
        self.close_time = self._parse_time(close_time)
        
        logger.info(f"MarketHoursChecker inicializado. Horario: {open_time}-{close_time} {market_timezone}")
    
    def _parse_time(self, time_str: str) -> time:
        """Convierte string HH:MM a objeto time."""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except (ValueError, AttributeError):
            logger.error(f"Formato de hora inválido: {time_str}. Usando 07:00 por defecto.")
            return time(7, 0)
    
    def is_market_open(self, check_time: Optional[datetime] = None) -> bool:
        """
        Verifica si el mercado está abierto.
        
        Args:
            check_time: Tiempo a verificar (None = ahora)
            
        Returns:
            True si el mercado está abierto, False si no
        """
        if check_time is None:
            check_time = datetime.now(self.market_timezone)
        elif check_time.tzinfo is None:
            check_time = self.market_timezone.localize(check_time)
        
        # Convertir a hora local del mercado
        market_time = check_time.astimezone(self.market_timezone)
        current_time = market_time.time()
        
        # Verificar si es día hábil (lunes a viernes)
        weekday = market_time.weekday()  # 0 = lunes, 6 = domingo
        is_weekday = 0 <= weekday <= 4
        
        # Verificar horario
        is_within_hours = self.open_time <= current_time < self.close_time
        
        # Verificar si es día festivo (implementación básica)
        is_holiday = self._is_holiday(market_time)
        
        market_open = is_weekday and is_within_hours and not is_holiday
        
        if market_open:
            logger.debug(f"Mercado abierto: {market_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.debug(f"Mercado cerrado: {market_time.strftime('%Y-%m-%d %H:%M:%S')} "
                        f"(weekday={is_weekday}, hours={is_within_hours}, holiday={is_holiday})")
        
        return market_open
    
    def _is_holiday(self, date: datetime) -> bool:
        """
        Verifica si es día festivo en México.
        
        Args:
            date: Fecha a verificar
            
        Returns:
            True si es día festivo, False si no
        """
        # Días festivos fijos en México (año 2026)
        # Esta es una lista simplificada - en producción usaríamos una API de días festivos
        fixed_holidays = [
            (1, 1),   # Año Nuevo
            (2, 5),   # Día de la Constitución (primer lunes de febrero)
            (3, 21),  # Natalicio de Benito Juárez (tercer lunes de marzo)
            (5, 1),   # Día del Trabajo
            (9, 16),  # Día de la Independencia
            (11, 20), # Revolución Mexicana (tercer lunes de noviembre)
            (12, 25), # Navidad
        ]
        
        month_day = (date.month, date.day)
        
        # Verificar días festivos fijos
        if month_day in fixed_holidays:
            return True
        
        # Días festivos variables (simplificado)
        # En producción, calcularíamos correctamente
        easter_2026 = datetime(2026, 4, 5)  # Domingo de Pascua 2026 (aproximado)
        holy_thursday = easter_2026 - timedelta(days=3)
        good_friday = easter_2026 - timedelta(days=2)
        
        if date.date() in [holy_thursday.date(), good_friday.date()]:
            return True
        
        return False
    
    def get_market_status(self) -> dict:
        """
        Obtiene el estado actual del mercado.
        
        Returns:
            Dict con información del estado del mercado
        """
        now = datetime.now(self.market_timezone)
        market_open = self.is_market_open(now)
        
        status = {
            "market_open": market_open,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": str(self.market_timezone),
            "open_time": self.open_time.strftime("%H:%M"),
            "close_time": self.close_time.strftime("%H:%M"),
            "weekday": now.strftime("%A"),
            "is_holiday": self._is_holiday(now)
        }
        
        if market_open:
            # Calcular tiempo hasta el cierre
            close_datetime = datetime.combine(now.date(), self.close_time)
            close_datetime = self.market_timezone.localize(close_datetime)
            time_to_close = close_datetime - now
            
            status["time_to_close"] = str(time_to_close)
            status["time_to_close_minutes"] = int(time_to_close.total_seconds() / 60)
        else:
            # Calcular tiempo hasta la próxima apertura
            next_open = self.get_next_open_time()
            if next_open:
                time_to_open = next_open - now
                status["next_open_time"] = next_open.strftime("%Y-%m-%d %H:%M:%S")
                status["time_to_open"] = str(time_to_open)
                status["time_to_open_minutes"] = int(time_to_open.total_seconds() / 60)
        
        return status
    
    def get_next_open_time(self) -> Optional[datetime]:
        """
        Calcula la próxima hora de apertura del mercado.
        
        Returns:
            Próxima datetime de apertura o None si no se puede calcular
        """
        now = datetime.now(self.market_timezone)
        
        # Si ya pasó la hora de cierre de hoy, buscar el próximo día hábil
        current_time = now.time()
        
        if current_time < self.open_time:
            # El mercado abrirá hoy
            next_open = datetime.combine(now.date(), self.open_time)
        elif current_time >= self.close_time:
            # El mercado cerró hoy, buscar próximo día hábil
            next_open = self._get_next_weekday(now.date() + timedelta(days=1))
        else:
            # El mercado está abierto ahora
            return now
        
        # Localizar datetime
        next_open = self.market_timezone.localize(next_open)
        
        # Verificar que no sea día festivo
        while self._is_holiday(next_open):
            next_open = self._get_next_weekday(next_open.date() + timedelta(days=1))
            next_open = self.market_timezone.localize(next_open)
        
        return next_open
    
    def _get_next_weekday(self, start_date: datetime.date) -> datetime:
        """
        Encuentra el próximo día hábil a partir de una fecha.
        
        Args:
            start_date: Fecha de inicio
            
        Returns:
            Próximo día hábil a las 8:00 AM
        """
        date = start_date
        
        while True:
            weekday = date.weekday()
            if 0 <= weekday <= 4:  # Lunes a viernes
                return datetime.combine(date, self.open_time)
            date += timedelta(days=1)
    
    def get_time_until_next_check(self, check_interval_minutes: int = 10) -> int:
        """
        Calcula segundos hasta el próximo check.
        
        Args:
            check_interval_minutes: Intervalo de check en minutos
            
        Returns:
            Segundos hasta el próximo check
        """
        now = datetime.now(self.market_timezone)
        
        if self.is_market_open(now):
            # Durante horario de mercado, usar intervalo normal
            return check_interval_minutes * 60
        else:
            # Fuera de horario, calcular hasta próxima apertura
            next_open = self.get_next_open_time()
            if next_open:
                time_to_open = (next_open - now).total_seconds()
                
                # Si la apertura es en menos de 1 hora, checkear cada 30 minutos
                if time_to_open < 3600:
                    return 1800  # 30 minutos
                # Si es en menos de 6 horas, checkear cada hora
                elif time_to_open < 6 * 3600:
                    return 3600  # 1 hora
                # Si es más lejano, checkear cada 4 horas
                else:
                    return 4 * 3600  # 4 horas
            
            # Fallback
            return 3600  # 1 hora