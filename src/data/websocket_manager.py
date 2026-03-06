import json
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import websocket
from enum import Enum

from utils.logger import logger


class WebSocketDataType(Enum):
    """Tipos de datos disponibles via WebSocket."""
    TICK = "tick"      # Datos de transacciones
    QUOTE = "quote"    # Cotizaciones en tiempo real
    DEPTH = "depth"    # Profundidad de mercado (order book)
    KLINE = "kline"    # Datos de velas (ej: kline@1 para 1 minuto)


class WebSocketManager:
    """
    Manager para conexión WebSocket de iTick.
    
    Maneja:
    1. Conexión y autenticación
    2. Suscripción a símbolos
    3. Recepción de datos en tiempo real
    4. Heartbeat (ping/pong)
    5. Reconexión automática
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "wss://api.itick.org/stock",
        max_symbols: int = 3,  # Límite del plan gratuito
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
        reconnect_backoff_factor: float = 1.5
    ):
        """
        Args:
            api_key: Token de autenticación de iTick
            base_url: URL del WebSocket
            max_symbols: Máximo número de símbolos a suscribir (3 en free tier)
            reconnect_interval: Segundos entre intentos de reconexión
            max_reconnect_attempts: Máximo número de intentos de reconexión
            reconnect_backoff_factor: Factor de backoff exponencial para reconexiones
        """
        self.api_key = api_key
        self.base_url = base_url
        self.max_symbols = min(max_symbols, 3)  # Forzar máximo 3 para free tier
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_backoff_factor = reconnect_backoff_factor
        
        # Estado de la conexión
        self.ws = None
        self.connected = False
        self.authenticated = False
        self.running = False
        
        # Estadísticas de reconexión
        self.reconnect_attempts = 0
        self.last_reconnect_time = None
        self.total_reconnects = 0
        self.last_error = None
        self.connection_start_time = None
        
        # Símbolos suscritos
        self.subscribed_symbols: List[str] = []
        self.subscribed_data_types: List[WebSocketDataType] = []
        
        # Callbacks para datos recibidos
        self.data_callbacks: Dict[WebSocketDataType, List[Callable]] = {
            WebSocketDataType.TICK: [],
            WebSocketDataType.QUOTE: [],
            WebSocketDataType.DEPTH: [],
            WebSocketDataType.KLINE: [],
        }
        
        # Cache de datos recibidos
        self.data_cache: Dict[str, Dict] = {}
        self.last_update_time: Dict[str, datetime] = {}
        
        # Thread para heartbeat
        self.heartbeat_thread = None
        self.last_ping_time = None
        
        logger.info(f"WebSocketManager inicializado. URL: {base_url}")
    
    def connect(self) -> bool:
        """Establece conexión WebSocket."""
        if self.connected:
            logger.warning("WebSocket ya está conectado")
            return True
        
        try:
            logger.info(f"Conectando a WebSocket: {self.base_url}")
            
            # Configurar headers de autenticación
            headers = {
                'token': self.api_key
            }
            
            # Crear conexión WebSocket
            self.ws = websocket.WebSocketApp(
                self.base_url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Iniciar thread de conexión
            self.running = True
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            
            # Esperar conexión (timeout de 10 segundos)
            for _ in range(20):
                if self.connected:
                    break
                time.sleep(0.5)
            
            if not self.connected:
                logger.error("Timeout al conectar WebSocket")
                return False
            
            logger.info("WebSocket conectado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error conectando WebSocket: {e}")
            return False
    
    def _run_websocket(self):
        """Ejecuta el loop del WebSocket."""
        try:
            self.ws.run_forever(
                ping_interval=30,    # Enviar ping cada 30 segundos
                ping_timeout=10,     # Timeout de ping
                reconnect=5          # Intentos de reconexión
            )
        except Exception as e:
            logger.error(f"Error en run_forever: {e}")
        finally:
            self.connected = False
            self.authenticated = False
    
    def _on_open(self, ws):
        """Callback cuando se abre la conexión."""
        logger.info("WebSocket connection opened")
        self.connected = True
        self.connection_start_time = datetime.now()
        self.last_error = None
        
        # Iniciar thread de heartbeat
        self._start_heartbeat()
    
    def _on_message(self, ws, message):
        """Callback cuando se recibe un mensaje."""
        try:
            data = json.loads(message)
            
            # Procesar diferentes tipos de mensajes
            if 'code' in data:
                code = data['code']
                
                if code == 1:  # Mensaje exitoso
                    if 'resAc' in data:
                        self._process_response(data)
                    elif 'data' in data:
                        self._process_data(data['data'])
                elif code == 0:  # Error
                    logger.error(f"Error en WebSocket: {data.get('msg', 'Unknown error')}")
                else:
                    logger.debug(f"Mensaje WebSocket: {data}")
            else:
                logger.warning(f"Mensaje WebSocket sin código: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando mensaje WebSocket: {e}")
        except Exception as e:
            logger.error(f"Error procesando mensaje WebSocket: {e}")
    
    def _process_response(self, response: Dict):
        """Procesa respuestas del servidor (auth, subscribe, etc)."""
        res_ac = response.get('resAc')
        msg = response.get('msg', '')
        
        if res_ac == 'auth':
            if response['code'] == 1:
                self.authenticated = True
                logger.info("WebSocket autenticado exitosamente")
                
                # Resuscribir símbolos si los hay
                if self.subscribed_symbols:
                    self._resubscribe()
            else:
                logger.error(f"Autenticación fallida: {msg}")
                self.authenticated = False
                
        elif res_ac == 'subscribe':
            if response['code'] == 1:
                logger.info(f"Suscripción exitosa: {msg}")
            else:
                logger.error(f"Error en suscripción: {msg}")
                
        elif res_ac == 'pong':
            logger.debug(f"Heartbeat recibido: {msg}")
            
        else:
            logger.debug(f"Respuesta WebSocket: {res_ac} - {msg}")
    
    def _process_data(self, data: Dict):
        """Procesa datos de mercado recibidos."""
        try:
            symbol = data.get('s')
            region = data.get('r')
            data_type = data.get('type')
            
            if not symbol or not data_type:
                logger.warning(f"Datos incompletos recibidos: {data}")
                return
            
            # Crear clave única para el símbolo
            symbol_key = f"{symbol}${region}" if region else symbol
            
            # Actualizar cache
            self.data_cache[symbol_key] = data
            self.last_update_time[symbol_key] = datetime.now()
            
            # Determinar tipo de datos
            ws_data_type = None
            if data_type == 'tick':
                ws_data_type = WebSocketDataType.TICK
            elif data_type == 'quote':
                ws_data_type = WebSocketDataType.QUOTE
            elif data_type == 'depth':
                ws_data_type = WebSocketDataType.DEPTH
            elif data_type.startswith('kline'):
                ws_data_type = WebSocketDataType.KLINE
            
            # Llamar callbacks
            if ws_data_type and ws_data_type in self.data_callbacks:
                for callback in self.data_callbacks[ws_data_type]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error en callback: {e}")
            
            # Log cada 100 mensajes para no saturar
            if len(self.data_cache) % 100 == 0:
                logger.debug(f"Datos recibidos: {len(self.data_cache)} símbolos en cache")
                
        except Exception as e:
            logger.error(f"Error procesando datos: {e}")
    
    def _on_error(self, ws, error):
        """Callback cuando ocurre un error."""
        logger.error(f"Error en WebSocket: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback cuando se cierra la conexión."""
        logger.info(f"WebSocket cerrado. Code: {close_status_code}, Msg: {close_msg}")
        self.connected = False
        self.authenticated = False
        
        # Intentar reconectar si aún está running
        if self.running:
            self.reconnect_attempts += 1
            self.total_reconnects += 1
            
            # Calcular backoff exponencial
            if self.reconnect_attempts > 1:
                backoff_time = min(
                    self.reconnect_interval * (self.reconnect_backoff_factor ** (self.reconnect_attempts - 1)),
                    300  # Máximo 5 minutos
                )
            else:
                backoff_time = self.reconnect_interval
            
            # Verificar si hemos excedido el máximo de intentos
            if self.reconnect_attempts > self.max_reconnect_attempts:
                logger.error(f"Excedido máximo de intentos de reconexión ({self.max_reconnect_attempts}). "
                           f"Deteniendo WebSocket.")
                self.running = False
                return
            
            logger.warning(f"Reconexión {self.reconnect_attempts}/{self.max_reconnect_attempts} "
                         f"en {backoff_time:.1f} segundos...")
            
            # Esperar con backoff
            time.sleep(backoff_time)
            
            # Intentar reconectar
            try:
                if self.connect():
                    self.reconnect_attempts = 0  # Resetear contador si reconexión exitosa
                    logger.info("Reconexión exitosa")
                else:
                    logger.error("Reconexión fallida")
            except Exception as e:
                logger.error(f"Error durante reconexión: {e}")
                self.last_error = str(e)
    
    def _start_heartbeat(self):
        """Inicia thread para enviar heartbeats."""
        def heartbeat_loop():
            while self.running and self.connected:
                try:
                    self._send_ping()
                    time.sleep(25)  # Enviar ping cada 25 segundos (menos de 30)
                except Exception as e:
                    logger.error(f"Error en heartbeat: {e}")
                    time.sleep(5)
        
        self.heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logger.info("Heartbeat thread iniciado")
    
    def _send_ping(self):
        """Envía ping para mantener la conexión activa."""
        if not self.connected or not self.ws:
            return
        
        try:
            timestamp = int(time.time() * 1000)
            ping_msg = {
                "ac": "ping",
                "params": str(timestamp)
            }
            
            self.ws.send(json.dumps(ping_msg))
            self.last_ping_time = datetime.now()
            logger.debug(f"Ping enviado: {timestamp}")
            
        except Exception as e:
            logger.error(f"Error enviando ping: {e}")
    
    def subscribe(
        self,
        symbols: List[str],
        data_types: List[WebSocketDataType] = None,
        prioritize_by: str = None
    ) -> bool:
        """
        Suscribe símbolos al WebSocket.
        
        Args:
            symbols: Lista de símbolos (formato: "AAPL$US" o ["AAPL$US", "TSLA$US"])
            data_types: Tipos de datos a suscribir (default: [QUOTE])
            prioritize_by: Criterio para priorizar símbolos cuando hay límite
                          None = primeros N, "market_cap" = por capitalización
        
        Returns:
            True si la suscripción fue exitosa
        """
        if not self.connected:
            logger.error("WebSocket no está conectado")
            return False
        
        if not self.authenticated:
            logger.error("WebSocket no está autenticado")
            return False
        
        if data_types is None:
            data_types = [WebSocketDataType.QUOTE]
        
        # Validar límite de símbolos (máximo 3 en free tier)
        if len(symbols) > self.max_symbols:
            logger.warning(f"Límite free tier: {len(symbols)} símbolos, usando {self.max_symbols}")
            
            # Priorizar símbolos si se especifica
            if prioritize_by == "market_cap" and hasattr(self, 'symbol_metadata'):
                # Ordenar por capitalización (asumiendo que tenemos metadata)
                symbols_with_metadata = []
                for symbol in symbols:
                    metadata = self.symbol_metadata.get(symbol, {})
                    market_cap = metadata.get('market_cap', 0)
                    symbols_with_metadata.append((symbol, market_cap))
                
                # Ordenar descendente por market cap
                symbols_with_metadata.sort(key=lambda x: x[1], reverse=True)
                symbols = [s[0] for s in symbols_with_metadata[:self.max_symbols]]
            else:
                # Tomar primeros N símbolos
                symbols = symbols[:self.max_symbols]
            
            logger.info(f"Símbolos priorizados: {', '.join(symbols)}")
        
        # Convertir data_types a strings
        type_strings = []
        for dt in data_types:
            if dt == WebSocketDataType.KLINE:
                type_strings.append("kline@1")  # 1-minuto klines
            else:
                type_strings.append(dt.value)
        
        # Crear mensaje de suscripción
        subscribe_msg = {
            "ac": "subscribe",
            "params": ",".join(symbols),
            "types": ",".join(type_strings)
        }
        
        try:
            self.ws.send(json.dumps(subscribe_msg))
            
            # Actualizar estado
            self.subscribed_symbols = symbols
            self.subscribed_data_types = data_types
            
            logger.info(f"Suscripto a {len(symbols)} símbolos: {', '.join(symbols[:5])}...")
            logger.info(f"Tipos de datos: {', '.join(type_strings)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error suscribiendo símbolos: {e}")
            return False
    
    def _resubscribe(self):
        """Resuscribe símbolos después de reconexión."""
        if self.subscribed_symbols:
            logger.info("Resuscribiendo símbolos después de reconexión")
            self.subscribe(self.subscribed_symbols, self.subscribed_data_types)
    
    def add_data_callback(
        self,
        data_type: WebSocketDataType,
        callback: Callable[[Dict], None]
    ):
        """
        Agrega un callback para datos recibidos.
        
        Args:
            data_type: Tipo de datos (TICK, QUOTE, DEPTH, KLINE)
            callback: Función que recibe los datos
        """
        if data_type in self.data_callbacks:
            self.data_callbacks[data_type].append(callback)
            logger.debug(f"Callback agregado para {data_type.value}")
    
    def get_latest_data(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene los datos más recientes para un símbolo.
        
        Args:
            symbol: Símbolo (formato: "AAPL$US")
        
        Returns:
            Datos más recientes o None si no hay
        """
        return self.data_cache.get(symbol)
    
    def get_all_data(self) -> Dict[str, Dict]:
        """Obtiene todos los datos en cache."""
        return self.data_cache.copy()
    
    def get_connection_stats(self) -> Dict:
        """Obtiene estadísticas de la conexión."""
        uptime = None
        if self.connection_start_time and self.connected:
            uptime = (datetime.now() - self.connection_start_time).total_seconds()
        
        return {
            "connected": self.connected,
            "authenticated": self.authenticated,
            "running": self.running,
            "reconnect_attempts": self.reconnect_attempts,
            "total_reconnects": self.total_reconnects,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "subscribed_symbols_count": len(self.subscribed_symbols),
            "data_cache_size": len(self.data_cache),
            "uptime_seconds": uptime,
            "last_error": self.last_error,
            "connection_start_time": self.connection_start_time
        }
    
    def cleanup(self):
        """Limpia recursos y cierra conexión."""
        logger.info("Limpiando WebSocketManager...")
        
        self.running = False
        
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        # Esperar a que se cierre
        time.sleep(1)
        
        self.connected = False
        self.authenticated = False
        
        logger.info("WebSocketManager limpiado")