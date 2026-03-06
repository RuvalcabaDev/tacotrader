"""
Manager para suscripciones rotativas de WebSocket.

Permite monitorear más de 3 símbolos con el plan gratuito de iTick
rotando entre grupos de símbolos cada cierto intervalo.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum

from utils.logger import logger
from data.websocket_manager import WebSocketManager, WebSocketDataType


class RotationStrategy(Enum):
    """Estrategias de rotación de suscripciones."""
    ROUND_ROBIN = "round_robin"      # Rotación circular simple
    MARKET_CAP_WEIGHTED = "market_cap_weighted"  # Más tiempo para símbolos con mayor market cap
    VOLATILITY_WEIGHTED = "volatility_weighted"  # Más tiempo para símbolos más volátiles
    HYBRID = "hybrid"                # Combinación de market cap y volatilidad


class RotatingSubscriptionManager:
    """
    Manager para suscripciones rotativas de WebSocket.
    
    Características:
    1. Divide símbolos en grupos de máximo 3 (límite free tier)
    2. Rota entre grupos cada intervalo configurable
    3. Prioriza símbolos por importancia (market cap, volatilidad, etc.)
    4. Mantiene cache de datos para todos los símbolos
    5. Proporciona acceso unificado a datos en tiempo real
    """
    
    def __init__(
        self,
        websocket_manager: WebSocketManager,
        rotation_interval_seconds: int = 60,  # Rotar cada 60 segundos
        max_symbols_per_group: int = 3,       # Límite free tier de iTick
        strategy: RotationStrategy = RotationStrategy.MARKET_CAP_WEIGHTED
    ):
        """
        Args:
            websocket_manager: Instancia de WebSocketManager
            rotation_interval_seconds: Segundos entre rotaciones
            max_symbols_per_group: Máximo símbolos por grupo (3 para free tier)
            strategy: Estrategia de rotación
        """
        self.ws_manager = websocket_manager
        self.rotation_interval = rotation_interval_seconds
        self.max_symbols_per_group = min(max_symbols_per_group, 3)  # Forzar máximo 3
        self.strategy = strategy
        
        # Estado de rotación
        self.all_symbols: List[str] = []
        self.symbol_groups: List[List[str]] = []
        self.current_group_index = 0
        self.rotation_running = False
        self.rotation_thread = None
        
        # Metadata para priorización
        self.symbol_metadata: Dict[str, Dict] = {}
        
        # Cache de datos
        self.data_cache: Dict[str, Dict] = {}
        self.last_update_time: Dict[str, datetime] = {}
        self.group_update_time: Dict[int, datetime] = {}
        
        # Estadísticas
        self.rotation_count = 0
        self.total_symbols_processed = 0
        
        logger.info(f"RotatingSubscriptionManager inicializado. "
                   f"Estrategia: {strategy.value}, "
                   f"Intervalo: {rotation_interval_seconds}s")
    
    def set_symbols(
        self,
        symbols: List[str],
        metadata: Optional[Dict[str, Dict]] = None
    ) -> bool:
        """
        Configura los símbolos a monitorear.
        
        Args:
            symbols: Lista de símbolos (formato: "AAPL$US")
            metadata: Metadata opcional para priorización
        
        Returns:
            True si los símbolos se configuraron exitosamente
        """
        if not symbols:
            logger.error("Lista de símbolos vacía")
            return False
        
        self.all_symbols = symbols.copy()
        
        if metadata:
            self.symbol_metadata = metadata.copy()
        
        # Crear grupos de símbolos
        self._create_symbol_groups()
        
        logger.info(f"Configurados {len(symbols)} símbolos en {len(self.symbol_groups)} grupos")
        logger.info(f"Tamaño de grupos: {[len(g) for g in self.symbol_groups]}")
        
        return True
    
    def _create_symbol_groups(self) -> None:
        """Crea grupos de símbolos basado en la estrategia de priorización."""
        if not self.all_symbols:
            return
        
        # Ordenar símbolos por prioridad según la estrategia
        prioritized_symbols = self._prioritize_symbols(self.all_symbols)
        
        # Dividir en grupos de máximo 3 símbolos
        self.symbol_groups = []
        for i in range(0, len(prioritized_symbols), self.max_symbols_per_group):
            group = prioritized_symbols[i:i + self.max_symbols_per_group]
            self.symbol_groups.append(group)
        
        logger.debug(f"Creados {len(self.symbol_groups)} grupos de símbolos")
    
    def _prioritize_symbols(self, symbols: List[str]) -> List[str]:
        """Prioriza símbolos según la estrategia configurada."""
        if self.strategy == RotationStrategy.ROUND_ROBIN:
            # Rotación simple, mantener orden original
            return symbols
        
        elif self.strategy == RotationStrategy.MARKET_CAP_WEIGHTED:
            # Ordenar por market cap (descendente)
            symbols_with_metadata = []
            for symbol in symbols:
                metadata = self.symbol_metadata.get(symbol, {})
                market_cap = metadata.get('market_cap', 0)
                symbols_with_metadata.append((symbol, market_cap))
            
            # Ordenar descendente por market cap
            symbols_with_metadata.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in symbols_with_metadata]
        
        elif self.strategy == RotationStrategy.VOLATILITY_WEIGHTED:
            # Ordenar por volatilidad (descendente)
            symbols_with_metadata = []
            for symbol in symbols:
                metadata = self.symbol_metadata.get(symbol, {})
                volatility = metadata.get('volatility', 0)
                symbols_with_metadata.append((symbol, volatility))
            
            # Ordenar descendente por volatilidad
            symbols_with_metadata.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in symbols_with_metadata]
        
        elif self.strategy == RotationStrategy.HYBRID:
            # Combinación de market cap y volatilidad
            symbols_with_score = []
            for symbol in symbols:
                metadata = self.symbol_metadata.get(symbol, {})
                market_cap = metadata.get('market_cap', 0)
                volatility = metadata.get('volatility', 0)
                
                # Ponderación: 70% market cap, 30% volatilidad
                market_cap_score = market_cap / 1_000_000_000  # Normalizar a billones
                volatility_score = volatility * 100  # Convertir a porcentaje
                
                score = (0.7 * market_cap_score) + (0.3 * volatility_score)
                symbols_with_score.append((symbol, score))
            
            # Ordenar descendente por score
            symbols_with_score.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in symbols_with_score]
        
        else:
            # Estrategia no reconocida, usar round robin
            logger.warning(f"Estrategia no reconocida: {self.strategy}, usando ROUND_ROBIN")
            return symbols
    
    def start_rotation(self) -> bool:
        """Inicia la rotación de suscripciones."""
        if not self.symbol_groups:
            logger.error("No hay grupos de símbolos configurados")
            return False
        
        if self.rotation_running:
            logger.warning("La rotación ya está en ejecución")
            return True
        
        logger.info(f"Iniciando rotación de suscripciones. "
                   f"{len(self.symbol_groups)} grupos, "
                   f"intervalo: {self.rotation_interval}s")
        
        self.rotation_running = True
        self.rotation_thread = threading.Thread(
            target=self._rotation_loop,
            daemon=True
        )
        self.rotation_thread.start()
        
        return True
    
    def stop_rotation(self) -> None:
        """Detiene la rotación de suscripciones."""
        self.rotation_running = False
        
        if self.rotation_thread:
            self.rotation_thread.join(timeout=5)
        
        logger.info("Rotación de suscripciones detenida")
    
    def _rotation_loop(self) -> None:
        """Loop principal de rotación."""
        while self.rotation_running:
            try:
                # Rotar al siguiente grupo
                self._rotate_to_next_group()
                
                # Esperar hasta la siguiente rotación
                for _ in range(self.rotation_interval):
                    if not self.rotation_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error en loop de rotación: {e}")
                time.sleep(5)
    
    def _rotate_to_next_group(self) -> None:
        """Rota al siguiente grupo de símbolos."""
        if not self.symbol_groups:
            return
        
        # Calcular siguiente índice
        self.current_group_index = (self.current_group_index + 1) % len(self.symbol_groups)
        current_group = self.symbol_groups[self.current_group_index]
        
        if not current_group:
            logger.warning(f"Grupo {self.current_group_index} vacío")
            return
        
        # Suscribir al grupo actual
        success = self.ws_manager.subscribe(
            symbols=current_group,
            data_types=[WebSocketDataType.QUOTE]
        )
        
        if success:
            self.rotation_count += 1
            self.total_symbols_processed += len(current_group)
            self.group_update_time[self.current_group_index] = datetime.now()
            
            logger.debug(f"Rotación {self.rotation_count}: "
                        f"Grupo {self.current_group_index + 1}/{len(self.symbol_groups)} "
                        f"({len(current_group)} símbolos)")
            
            # Log cada 10 rotaciones para no saturar
            if self.rotation_count % 10 == 0:
                logger.info(f"Rotaciones completadas: {self.rotation_count}, "
                           f"Símbolos procesados: {self.total_symbols_processed}")
        else:
            logger.error(f"Error suscribiendo grupo {self.current_group_index}")
    
    def add_data_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Agrega callback para datos recibidos.
        
        Args:
            callback: Función que recibe datos de símbolos
        """
        # Registrar callback en WebSocket manager
        self.ws_manager.add_data_callback(WebSocketDataType.QUOTE, callback)
        
        # También cachear datos localmente
        def caching_callback(data: Dict) -> None:
            try:
                symbol = data.get('s')
                region = data.get('r')
                
                if symbol and region:
                    symbol_key = f"{symbol}${region}"
                    self.data_cache[symbol_key] = data
                    self.last_update_time[symbol_key] = datetime.now()
                    
                    # Llamar callback original
                    callback(data)
                    
            except Exception as e:
                logger.error(f"Error en caching callback: {e}")
        
        # Reemplazar callback con versión que cachea
        self.ws_manager.data_callbacks[WebSocketDataType.QUOTE] = [caching_callback]
    
    def get_latest_data(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene los datos más recientes para un símbolo.
        
        Args:
            symbol: Símbolo (formato: "AAPL$US")
        
        Returns:
            Datos más recientes o None si no hay
        """
        # Primero intentar cache local
        if symbol in self.data_cache:
            return self.data_cache[symbol]
        
        # Luego intentar WebSocket manager
        return self.ws_manager.get_latest_data(symbol)
    
    def get_all_cached_data(self) -> Dict[str, Dict]:
        """Obtiene todos los datos en cache."""
        return self.data_cache.copy()
    
    def get_rotation_status(self) -> Dict:
        """Obtiene el estado de la rotación."""
        current_group = self.symbol_groups[self.current_group_index] if self.symbol_groups else []
        
        return {
            "rotation_running": self.rotation_running,
            "current_group_index": self.current_group_index,
            "current_group_size": len(current_group),
            "current_group_symbols": current_group,
            "total_groups": len(self.symbol_groups),
            "total_symbols": len(self.all_symbols),
            "rotation_count": self.rotation_count,
            "total_symbols_processed": self.total_symbols_processed,
            "rotation_interval_seconds": self.rotation_interval,
            "strategy": self.strategy.value,
            "last_group_update": self.group_update_time.get(self.current_group_index),
            "cache_size": len(self.data_cache)
        }
    
    def cleanup(self) -> None:
        """Limpia recursos."""
        self.stop_rotation()
        logger.info("RotatingSubscriptionManager limpiado")