import json
import os
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path

from utils.logger import logger
from data.itick_provider import ITickProvider


class SymbolManager:
    """
    Gestor de símbolos BMV.
    
    Responsabilidades:
    1. Obtener y mantener lista de símbolos BMV
    2. Filtrar top 100 por capitalización (estimada)
    3. Actualizar lista periódicamente
    4. Persistir en archivo para evitar requests innecesarias
    """
    
    def __init__(
        self,
        data_provider: ITickProvider,
        data_dir: str = "data",
        max_symbols: int = 100,
        refresh_hours: int = 24
    ):
        """
        Args:
            data_provider: Provider para obtener datos
            data_dir: Directorio para almacenar datos
            max_symbols: Máximo número de símbolos a mantener
            refresh_hours: Horas entre refrescos de la lista
        """
        self.data_provider = data_provider
        self.data_dir = Path(data_dir)
        self.max_symbols = max_symbols
        self.refresh_hours = refresh_hours
        
        # Asegurar que el directorio existe
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de persistencia
        self.symbols_file = self.data_dir / "bmv_symbols.json"
        
        # Cache en memoria
        self.symbols: List[Dict] = []
        self.last_update: Optional[datetime] = None
        
        logger.info(f"SymbolManager inicializado. Máx símbolos: {max_symbols}")
    
    def _load_symbols_from_file(self) -> bool:
        """
        Carga símbolos desde archivo.
        
        Returns:
            True si se cargaron exitosamente, False si no
        """
        if not self.symbols_file.exists():
            logger.debug("Archivo de símbolos no encontrado")
            return False
        
        try:
            with open(self.symbols_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verificar estructura
            if 'symbols' not in data or 'last_update' not in data:
                logger.warning("Archivo de símbolos corrupto")
                return False
            
            # Cargar símbolos
            self.symbols = data['symbols'][:self.max_symbols]
            
            # Parsear fecha de última actualización
            last_update_str = data['last_update']
            self.last_update = datetime.fromisoformat(last_update_str)
            
            logger.info(f"Símbolos cargados desde archivo ({len(self.symbols)} símbolos)")
            logger.info(f"Última actualización: {self.last_update}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cargando símbolos desde archivo: {e}")
            return False
    
    def _save_symbols_to_file(self) -> bool:
        """
        Guarda símbolos en archivo.
        
        Returns:
            True si se guardó exitosamente, False si no
        """
        try:
            data = {
                'symbols': self.symbols,
                'last_update': datetime.now().isoformat(),
                'metadata': {
                    'total_symbols': len(self.symbols),
                    'max_symbols': self.max_symbols,
                    'provider': 'iTick',
                    'region': 'MX'
                }
            }
            
            with open(self.symbols_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Símbolos guardados en {self.symbols_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando símbolos en archivo: {e}")
            return False
    
    def _needs_refresh(self) -> bool:
        """
        Verifica si se necesita refrescar la lista de símbolos.
        
        Returns:
            True si necesita refresco, False si no
        """
        if not self.last_update:
            return True
        
        time_since_update = datetime.now() - self.last_update
        return time_since_update > timedelta(hours=self.refresh_hours)
    
    def _estimate_market_cap(self, symbol_data: Dict) -> float:
        """
        Estima capitalización de mercado basado en datos disponibles.
        
        Args:
            symbol_data: Datos del símbolo
            
        Returns:
            Capitalización estimada en MXN (0 si no se puede estimar)
        """
        # En una implementación real, esto obtendría datos fundamentales
        # Por ahora, usamos una estimación basada en el nombre/volumen
        
        code = symbol_data.get('code', '').upper()
        name = symbol_data.get('name', '').upper()
        
        # Empresas grandes conocidas (prioridad alta)
        large_caps = {
            'WALMEX': 1000,  # Walmart México
            'AMXL': 800,      # América Móvil
            'GFNORTEO': 300,  # Banorte
            'GMEXICOB': 250,  # Grupo México
            'FEMSAUBD': 400,  # FEMSA
            'TLEVISACPO': 150, # Televisa
            'BIMBOA': 200,    # Grupo Bimbo
            'KIMBERA': 120,   # Kimberly-Clark
            'ALPEKA': 80,     # Alpek
            'CEMEXCPO': 180,  # Cemex
        }
        
        # Buscar coincidencia exacta
        if code in large_caps:
            return large_caps[code]
        
        # Buscar por nombre
        for large_code, cap in large_caps.items():
            if large_code in name or code in name:
                return cap
        
        # Estimación por sector/industria basada en código
        # (esto es muy simplificado, en producción usaríamos datos reales)
        if code.startswith('G'):  # Posiblemente grupos financieros/industriales
            return 50
        elif code.startswith('C'):  # Posiblemente constructoras/comerciales
            return 30
        elif code.startswith('A'):  # Posiblemente alimenticias/automotrices
            return 40
        else:
            return 20  # Capitalización pequeña por defecto
    
    def _filter_and_sort_symbols(self, symbols: List[Dict]) -> List[Dict]:
        """
        Filtra y ordena símbolos por capitalización estimada.
        
        Args:
            symbols: Lista de símbolos crudos
            
        Returns:
            Lista filtrada y ordenada
        """
        # Estimación de capitalización para cada símbolo
        symbols_with_cap = []
        
        for symbol in symbols:
            code = symbol.get('code', '')
            
            # Saltar símbolos vacíos o inválidos
            if not code or len(code) < 2:
                continue
            
            # Estimación de capitalización
            estimated_cap = self._estimate_market_cap(symbol)
            
            symbols_with_cap.append({
                **symbol,
                'estimated_cap_mxn_b': estimated_cap,
                'priority': estimated_cap  # Usar para ordenar
            })
        
        # Ordenar por capitalización estimada (descendente)
        symbols_with_cap.sort(key=lambda x: x['priority'], reverse=True)
        
        # Tomar top N
        filtered_symbols = symbols_with_cap[:self.max_symbols]
        
        logger.info(f"Filtrados {len(filtered_symbols)} símbolos de {len(symbols)}")
        
        return filtered_symbols
    
    def get_symbols(self, force_refresh: bool = False) -> List[Dict]:
        """
        Obtiene la lista de símbolos BMV.
        
        Args:
            force_refresh: Forzar refresco desde la API
            
        Returns:
            Lista de símbolos filtrados y ordenados
        """
        # Verificar si necesitamos refrescar
        needs_refresh = force_refresh or self._needs_refresh()
        
        if not needs_refresh and self.symbols:
            logger.debug("Usando símbolos en cache")
            return self.symbols
        
        # Intentar cargar desde archivo primero (si no force_refresh)
        if not force_refresh and self._load_symbols_from_file():
            if not self._needs_refresh():
                return self.symbols
        
        # Obtener desde la API
        logger.info("Obteniendo símbolos desde iTick API...")
        
        try:
            raw_symbols = self.data_provider.get_symbols(force_refresh=True)
            
            if not raw_symbols:
                logger.error("No se pudieron obtener símbolos desde la API")
                # Usar cache existente si hay
                if self.symbols:
                    return self.symbols
                return []
            
            # Filtrar y ordenar
            self.symbols = self._filter_and_sort_symbols(raw_symbols)
            self.last_update = datetime.now()
            
            # Guardar en archivo
            self._save_symbols_to_file()
            
            logger.info(f"Obtenidos {len(self.symbols)} símbolos BMV")
            return self.symbols
            
        except Exception as e:
            logger.error(f"Error obteniendo símbolos: {e}")
            
            # Intentar usar cache de archivo como fallback
            if self._load_symbols_from_file():
                return self.symbols
            
            return []
    
    def get_symbol_codes(self, force_refresh: bool = False) -> List[str]:
        """
        Obtiene solo los códigos de los símbolos.
        
        Args:
            force_refresh: Forzar refresco
            
        Returns:
            Lista de códigos de símbolos
        """
        symbols = self.get_symbols(force_refresh)
        return [symbol['code'] for symbol in symbols]
    
    def get_symbol_info(self, symbol_code: str) -> Optional[Dict]:
        """
        Obtiene información de un símbolo específico.
        
        Args:
            symbol_code: Código del símbolo
            
        Returns:
            Información del símbolo o None si no existe
        """
        symbols = self.get_symbols()
        
        for symbol in symbols:
            if symbol['code'] == symbol_code:
                return symbol
        
        return None
    
    def update_symbol_metadata(self, symbol_code: str, metadata: Dict) -> bool:
        """
        Actualiza metadatos de un símbolo.
        
        Args:
            symbol_code: Código del símbolo
            metadata: Metadatos a actualizar
            
        Returns:
            True si se actualizó, False si no
        """
        symbols = self.get_symbols()
        
        for i, symbol in enumerate(symbols):
            if symbol['code'] == symbol_code:
                symbols[i].update(metadata)
                self.symbols = symbols
                self._save_symbols_to_file()
                return True
        
        return False
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de los símbolos.
        
        Returns:
            Dict con estadísticas
        """
        symbols = self.get_symbols()
        
        # Agrupar por sector (si está disponible)
        sectors = {}
        for symbol in symbols:
            sector = symbol.get('sector', 'Desconocido')
            sectors[sector] = sectors.get(sector, 0) + 1
        
        # Calcular capitalización total estimada
        total_cap = sum(symbol.get('estimated_cap_mxn_b', 0) for symbol in symbols)
        
        return {
            'total_symbols': len(symbols),
            'total_cap_estimated_b_mxn': total_cap,
            'avg_cap_per_symbol_b_mxn': total_cap / len(symbols) if symbols else 0,
            'sectors': sectors,
        }
    
    def get_top_symbols_for_websocket(self, count: int = 30) -> List[str]:
        """
        Obtiene los símbolos más importantes para monitoreo via WebSocket.
        
        Args:
            count: Número de símbolos a retornar
        
        Returns:
            Lista de códigos de símbolos
        """
        symbols = self.get_symbols()
        
        # Ordenar por capitalización estimada (ya está ordenado)
        top_symbols = symbols[:count]
        
        # Extraer códigos de símbolos
        symbol_codes = [symbol['code'] for symbol in top_symbols]
        
        logger.info(f"Seleccionados {len(symbol_codes)} símbolos para WebSocket")
        logger.debug(f"Top {min(5, len(symbol_codes))} símbolos: {', '.join(symbol_codes[:5])}")
        
        return symbol_codes
    
    def get_symbol_metadata_for_websocket(self, symbol_codes: List[str]) -> List[Dict]:
        """
        Obtiene metadatos de símbolos para priorización en WebSocket.
        
        Args:
            symbol_codes: Lista de códigos de símbolos
        
        Returns:
            Lista de metadatos
        """
        symbols = self.get_symbols()
        
        metadata = []
        for symbol_code in symbol_codes:
            symbol = self.get_symbol_info(symbol_code)
            if symbol:
                metadata.append({
                    'code': symbol_code,
                    'market_cap': symbol.get('estimated_cap_mxn_b', 0),
                    'name': symbol.get('name', ''),
                    'volatility': symbol.get('volatility', 0)  # Se puede calcular después
                })
        
        return metadata