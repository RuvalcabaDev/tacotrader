import requests
import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from utils.logger import logger
from utils.rate_limiter import itick_rate_limiter
from data.base_provider import BaseDataProvider
from data.websocket_manager import WebSocketManager, WebSocketDataType
from data.rotating_subscription import RotatingSubscriptionManager, RotationStrategy


class ITickProvider(BaseDataProvider):
    """
    Data provider para la API de iTick.
    
    Soporta:
    1. REST API con rate limiting (5 requests/minuto en free tier)
    2. WebSocket para datos en tiempo real (opcional)
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.itick.org",
        use_websocket: bool = False,
        max_symbols: int = 100
    ):
        """
        Args:
            api_key: Token de autenticación de iTick
            base_url: URL base de la API
            use_websocket: Usar WebSocket en lugar de REST (más eficiente)
            max_symbols: Máximo número de símbolos a monitorear
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.use_websocket = use_websocket
        self.max_symbols = max_symbols
        
        # Headers para requests REST
        self.headers = {
            'accept': 'application/json',
            'token': api_key
        }
        
        # Cache para símbolos y datos
        self.symbols_cache: Optional[List[Dict]] = None
        self.symbols_cache_time: Optional[datetime] = None
        self.quote_cache: Dict[str, Dict] = {}
        self.quote_cache_time: Dict[str, datetime] = {}
        
        # WebSocket Manager
        self.ws_manager = None
        self.rotating_manager = None
        if use_websocket:
            self._init_websocket()
        
        logger.info(f"ITickProvider inicializado. WebSocket: {use_websocket}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Realiza una petición HTTP con rate limiting.
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros de query
            
        Returns:
            Respuesta de la API como dict
        """
        # Respetar rate limiting
        itick_rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Realizando request: {url}")
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            # Registrar la petición
            itick_rate_limiter.record_request()
            
            if response.status_code != 200:
                logger.error(f"Error en request: {response.status_code} - {response.text[:200]}")
                return {"code": response.status_code, "msg": "HTTP Error", "data": None}
            
            data = response.json()
            
            # Verificar código de respuesta de iTick
            if data.get("code") != 0:
                logger.warning(f"iTick API error: {data.get('msg')}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout en request: {url}")
            return {"code": 408, "msg": "Timeout", "data": None}
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error en request: {url}")
            return {"code": 503, "msg": "Connection Error", "data": None}
        except Exception as e:
            logger.error(f"Error en request {url}: {e}")
            return {"code": 500, "msg": str(e), "data": None}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
    )
    def get_symbols(self, force_refresh: bool = False) -> List[Dict]:
        """
        Obtiene la lista de símbolos BMV.
        
        Args:
            force_refresh: Forzar refresco del cache
            
        Returns:
            Lista de símbolos con información básica
        """
        # Verificar cache (refrescar una vez al día)
        if not force_refresh and self.symbols_cache and self.symbols_cache_time:
            cache_age = datetime.now() - self.symbols_cache_time
            if cache_age < timedelta(hours=24):
                logger.debug(f"Usando cache de símbolos (edad: {cache_age})")
                return self.symbols_cache[:self.max_symbols]
        
        logger.info("Obteniendo lista de símbolos BMV desde iTick...")
        
        params = {
            'type': 'stock',
            'region': 'MX'
        }
        
        response = self._make_request("/symbol/list", params)
        
        if response.get("code") == 0 and response.get("data"):
            symbols = response["data"]
            
            # Filtrar solo acciones (no índices) y ordenar
            stock_symbols = []
            for symbol in symbols:
                if isinstance(symbol, dict) and symbol.get('t') == 'stock':
                    # Extraer código limpio
                    code = symbol.get('c', '')
                    name = symbol.get('n', '')
                    
                    # Filtrar índices (contienen "Index" en el nombre)
                    if 'Index' not in name and code:
                        stock_symbols.append({
                            'code': code,
                            'name': name,
                            'exchange': symbol.get('e', 'BMV'),
                            'sector': symbol.get('s'),
                            'listing': symbol.get('l')
                        })
            
            # Ordenar alfabéticamente por código
            stock_symbols.sort(key=lambda x: x['code'])
            
            # Limitar al máximo configurado
            self.symbols_cache = stock_symbols[:self.max_symbols]
            self.symbols_cache_time = datetime.now()
            
            logger.info(f"Obtenidos {len(self.symbols_cache)} símbolos BMV")
            return self.symbols_cache
        else:
            logger.error(f"Error obteniendo símbolos: {response.get('msg')}")
            return []
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5)
    )
    def get_quote(self, symbol_code: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Obtiene quote de un símbolo específico.
        
        Prioridad:
        1. WebSocket (datos en tiempo real)
        2. Cache (datos recientes)
        3. REST API (fallback)
        
        Args:
            symbol_code: Código del símbolo (ej: 'WALMEX', 'GRUMAB')
            use_cache: Usar cache si los datos son recientes
            
        Returns:
            Datos del quote o None si hay error
        """
        # 1. Primero intentar WebSocket (datos en tiempo real)
        if self.ws_manager and self.ws_manager.connected:
            realtime_data = self.get_realtime_quote(symbol_code)
            if realtime_data:
                logger.debug(f"Usando WebSocket para {symbol_code}")
                
                # Formatear datos para compatibilidad
                formatted_data = self._format_websocket_data(realtime_data)
                if formatted_data:
                    # Actualizar cache
                    self.quote_cache[symbol_code] = formatted_data
                    self.quote_cache_time[symbol_code] = datetime.now()
                    return formatted_data
        
        # 2. Verificar cache (5 minutos por defecto)
        if use_cache and symbol_code in self.quote_cache:
            cache_time = self.quote_cache_time.get(symbol_code)
            if cache_time and (datetime.now() - cache_time) < timedelta(minutes=5):
                logger.debug(f"Usando cache para {symbol_code}")
                return self.quote_cache[symbol_code]
        
        # 3. Usar REST API como fallback
        logger.debug(f"Obteniendo quote via REST API para {symbol_code}")
        
        params = {
            'region': 'MX',
            'code': symbol_code
        }
        
        response = self._make_request("/stock/quote", params)
        
        if response.get("code") == 0 and response.get("data"):
            quote_data = response["data"]
            
            # Parsear timestamp
            timestamp_ms = quote_data.get('t', 0)
            if timestamp_ms:
                quote_data['timestamp'] = datetime.fromtimestamp(timestamp_ms / 1000)
            else:
                quote_data['timestamp'] = datetime.now()
            
            # Calcular movimiento porcentual si no está presente
            if 'chp' not in quote_data or quote_data['chp'] is None:
                last_price = quote_data.get('ld')
                current_price = quote_data.get('p')
                if last_price and current_price and last_price > 0:
                    quote_data['chp'] = ((current_price - last_price) / last_price) * 100
            
            # Actualizar cache
            self.quote_cache[symbol_code] = quote_data
            self.quote_cache_time[symbol_code] = datetime.now()
            
            return quote_data
        else:
            logger.warning(f"No se pudo obtener quote para {symbol_code}: {response.get('msg')}")
            return None
    
    def get_batch_quotes(self, symbol_codes: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Obtiene quotes para múltiples símbolos.
        
        Prioridad:
        1. WebSocket (datos en tiempo real para todos los símbolos)
        2. REST API con rate limiting (fallback)
        
        Args:
            symbol_codes: Lista de códigos de símbolos
            
        Returns:
            Dict con símbolo como key y quote como value
        """
        results = {}
        
        # 1. Intentar obtener todos los datos via WebSocket primero
        if self.ws_manager and self.ws_manager.connected:
            logger.debug(f"Obteniendo {len(symbol_codes)} quotes via WebSocket")
            
            for symbol_code in symbol_codes:
                realtime_data = self.get_realtime_quote(symbol_code)
                if realtime_data:
                    formatted_data = self._format_websocket_data(realtime_data)
                    if formatted_data:
                        results[symbol_code] = formatted_data
                        # Actualizar cache
                        self.quote_cache[symbol_code] = formatted_data
                        self.quote_cache_time[symbol_code] = datetime.now()
                    else:
                        results[symbol_code] = None
                else:
                    results[symbol_code] = None
            
            # Verificar cuántos obtuvimos via WebSocket
            successful = sum(1 for v in results.values() if v is not None)
            if successful > 0:
                logger.debug(f"WebSocket: {successful}/{len(symbol_codes)} quotes obtenidos")
                
                # Si obtuvimos todos, retornar
                if successful == len(symbol_codes):
                    return results
        
        # 2. Usar REST API para los que faltan
        logger.debug(f"Usando REST API para quotes faltantes")
        
        for symbol_code in symbol_codes:
            # Si ya tenemos datos via WebSocket, saltar
            if symbol_code in results and results[symbol_code] is not None:
                continue
            
            # Respetar rate limiting entre peticiones
            remaining = itick_rate_limiter.get_remaining_requests()
            if remaining <= 1:
                # Esperar un poco si estamos cerca del límite
                time_to_reset = itick_rate_limiter.get_time_to_next_reset()
                if time_to_reset > 0:
                    logger.debug(f"Rate limit bajo. Esperando {time_to_reset:.1f}s")
                    time.sleep(time_to_reset + 0.5)
            
            quote = self.get_quote(symbol_code)
            results[symbol_code] = quote
            
            # Pequeña pausa entre peticiones para ser amigables
            time.sleep(0.1)
        
        return results
    
    def get_rate_limit_status(self) -> Dict:
        """
        Obtiene el estado del rate limiting.
        
        Returns:
            Dict con información del rate limit
        """
        return itick_rate_limiter.get_status()
    
    # ============================================================================
    # WebSocket Methods
    # ============================================================================
    
    def _init_websocket(self):
        """Inicializa el WebSocket Manager y Rotating Subscription Manager."""
        try:
            self.ws_manager = WebSocketManager(
                api_key=self.api_key,
                base_url="wss://api.itick.org/stock",
                max_symbols=3,  # Free tier solo permite 3 símbolos simultáneos
                reconnect_interval=5
            )
            
            # Inicializar rotating subscription manager
            self.rotating_manager = RotatingSubscriptionManager(
                websocket_manager=self.ws_manager,
                rotation_interval_seconds=15,  # Rotar cada 15 segundos (más frecuente)
                max_symbols_per_group=3,       # Límite free tier
                strategy=RotationStrategy.MARKET_CAP_WEIGHTED
            )
            
            # Agregar callback para datos de quotes
            self.rotating_manager.add_data_callback(self._on_websocket_data)
            
            # Conectar WebSocket
            if self.ws_manager.connect():
                logger.info("WebSocket Manager inicializado y conectado")
            else:
                logger.warning("No se pudo conectar WebSocket, usando REST API")
                self.ws_manager = None
                self.rotating_manager = None
                
        except Exception as e:
            logger.error(f"Error inicializando WebSocket: {e}")
            self.ws_manager = None
            self.rotating_manager = None
    
    def _on_websocket_data(self, data: Dict):
        """Callback cuando se reciben datos del WebSocket."""
        try:
            symbol = data.get('s')
            region = data.get('r')
            
            if not symbol:
                return
            
            # Crear clave del símbolo
            symbol_key = f"{symbol}${region}" if region else symbol
            
            # Actualizar cache
            self.quote_cache[symbol_key] = data
            self.quote_cache_time[symbol_key] = datetime.now()
            
            # Log cada 50 actualizaciones
            if len(self.quote_cache) % 50 == 0:
                logger.debug(f"WebSocket: {len(self.quote_cache)} símbolos actualizados")
                
        except Exception as e:
            logger.error(f"Error procesando datos WebSocket: {e}")
    
    def subscribe_symbols(self, symbols: List[str], symbol_metadata: List[Dict] = None) -> bool:
        """
        Suscribe símbolos al WebSocket usando rotating subscriptions.
        
        Args:
            symbols: Lista de símbolos (ej: ["WALMEX", "AC", "GFNORTE"])
            symbol_metadata: Metadata opcional para priorizar por capitalización
        
        Returns:
            True si la suscripción fue exitosa
        """
        if not self.ws_manager or not self.rotating_manager:
            logger.warning("WebSocket no está habilitado")
            return False
        
        # Si tenemos metadata, crear diccionario para priorización
        metadata_dict = {}
        if symbol_metadata:
            for meta in symbol_metadata:
                symbol_code = meta.get('code') or meta.get('c')
                if symbol_code:
                    metadata_dict[symbol_code] = {
                        'market_cap': meta.get('market_cap', 0),
                        'name': meta.get('name') or meta.get('n', ''),
                        'volatility': meta.get('volatility', 0)  # Para estrategias híbridas
                    }
        
        # Convertir símbolos BMV al formato iTick
        formatted_symbols = []
        for symbol in symbols:
            # Para BMV, el formato es "WALMEX$MX"
            if symbol.endswith(".MX"):
                symbol = symbol.replace(".MX", "")
            formatted_symbols.append(f"{symbol}$MX")
        
        # Configurar símbolos en rotating manager
        success = self.rotating_manager.set_symbols(
            symbols=formatted_symbols,
            metadata=metadata_dict
        )
        
        if success:
            # Iniciar rotación
            rotation_success = self.rotating_manager.start_rotation()
            
            if rotation_success:
                total_symbols = len(formatted_symbols)
                total_groups = len(self.rotating_manager.symbol_groups)
                logger.info(f"Rotating subscriptions iniciado. "
                           f"{total_symbols} símbolos en {total_groups} grupos, "
                           f"rotando cada 30 segundos")
                
                # Log primeros grupos
                if self.rotating_manager.symbol_groups:
                    for i, group in enumerate(self.rotating_manager.symbol_groups[:3]):
                        logger.info(f"  Grupo {i+1}: {', '.join(group)}")
                    if total_groups > 3:
                        logger.info(f"  ... y {total_groups - 3} grupos más")
            else:
                logger.error("Error iniciando rotación de suscripciones")
                success = False
        
        return success
    
    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene quote en tiempo real desde WebSocket (si disponible).
        
        Args:
            symbol: Símbolo (ej: "WALMEX" o "WALMEX.MX")
        
        Returns:
            Datos del quote o None si no hay
        """
        if not self.ws_manager:
            return None
        
        # Formatear símbolo para WebSocket
        if symbol.endswith(".MX"):
            symbol = symbol.replace(".MX", "")
        symbol_key = f"{symbol}$MX"
        
        # Primero intentar rotating manager
        if self.rotating_manager:
            data = self.rotating_manager.get_latest_data(symbol_key)
            if data:
                return data
        
        # Luego intentar WebSocket manager directo
        if self.ws_manager:
            return self.ws_manager.get_latest_data(symbol_key)
        
        return None
    
    def is_websocket_connected(self) -> bool:
        """Verifica si el WebSocket está conectado."""
        return self.ws_manager is not None and self.ws_manager.connected
    
    def _format_websocket_data(self, ws_data: Dict) -> Optional[Dict]:
        """
        Formatea datos del WebSocket al formato esperado por la aplicación.
        
        Args:
            ws_data: Datos crudos del WebSocket
            
        Returns:
            Datos formateados o None si no son válidos
        """
        try:
            # Extraer campos básicos
            symbol = ws_data.get('s')
            region = ws_data.get('r')
            data_type = ws_data.get('type')
            
            if not symbol or data_type != 'quote':
                return None
            
            # Crear estructura compatible con REST API
            formatted_data = {
                's': symbol,
                'r': region,
                'ld': ws_data.get('ld', 0),          # Last price
                'o': ws_data.get('o', 0),            # Open
                'h': ws_data.get('h', 0),            # High
                'l': ws_data.get('l', 0),            # Low
                't': ws_data.get('t', 0),            # Timestamp (ms)
                'v': ws_data.get('v', 0),            # Volume
                'tu': ws_data.get('tu', 0),          # Turnover
                'ts': ws_data.get('ts', 0),          # Trading status
                'p': ws_data.get('p', 0),            # Previous close
                'ch': ws_data.get('ch', 0),          # Change
                'chp': ws_data.get('chp', 0),        # Change %
                'type': 'quote'
            }
            
            # Parsear timestamp
            timestamp_ms = formatted_data.get('t', 0)
            if timestamp_ms:
                formatted_data['timestamp'] = datetime.fromtimestamp(timestamp_ms / 1000)
            else:
                formatted_data['timestamp'] = datetime.now()
            
            # Asegurar que tenemos precio actual
            if formatted_data['ld'] == 0 and formatted_data['p'] > 0:
                formatted_data['ld'] = formatted_data['p']
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error formateando datos WebSocket: {e}")
            return None
    
    def get_websocket_status(self) -> Dict:
        """Obtiene el estado del WebSocket y rotating subscriptions."""
        if not self.ws_manager:
            return {"enabled": False, "connected": False}
        
        # Obtener estadísticas de conexión
        connection_stats = self.ws_manager.get_connection_stats()
        
        status = {
            "enabled": True,
            "connected": self.ws_manager.connected,
            "authenticated": self.ws_manager.authenticated,
            "subscribed_symbols": len(self.ws_manager.subscribed_symbols),
            "data_cache_size": len(self.ws_manager.get_all_data()),
            "connection_stats": connection_stats
        }
        
        # Agregar estado de rotating subscriptions si está habilitado
        if self.rotating_manager:
            rotation_status = self.rotating_manager.get_rotation_status()
            status.update({
                "rotating_enabled": True,
                "rotation_status": rotation_status,
                "total_symbols_monitored": len(self.rotating_manager.all_symbols),
                "rotation_groups": len(self.rotating_manager.symbol_groups),
                "rotation_count": rotation_status.get("rotation_count", 0)
            })
        else:
            status["rotating_enabled"] = False
        
        return status
    
    def cleanup(self):
        """Limpia recursos (cierra WebSocket si está activo)."""
        if self.rotating_manager:
            self.rotating_manager.cleanup()
            logger.info("Rotating Subscription Manager limpiado")
        
        if self.ws_manager:
            self.ws_manager.cleanup()
            logger.info("WebSocket Manager limpiado")
        
        # Limpiar caches viejos
        cutoff_time = datetime.now() - timedelta(hours=1)
        old_symbols = [
            sym for sym, time in self.quote_cache_time.items()
            if time < cutoff_time
        ]
        
        for sym in old_symbols:
            self.quote_cache.pop(sym, None)
            self.quote_cache_time.pop(sym, None)
        
        logger.debug("Cache limpiado")