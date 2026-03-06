from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseDataProvider(ABC):
    """
    Interfaz base para todos los data providers.
    
    Define los métodos que deben implementar todos los providers
    para ser compatibles con TacoTrader.
    """
    
    @abstractmethod
    def get_symbols(self, force_refresh: bool = False) -> List[Dict]:
        """
        Obtiene la lista de símbolos disponibles.
        
        Args:
            force_refresh: Forzar refresco del cache
            
        Returns:
            Lista de símbolos con información básica
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbol_code: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Obtiene quote de un símbolo específico.
        
        Args:
            symbol_code: Código del símbolo
            use_cache: Usar cache si los datos son recientes
            
        Returns:
            Datos del quote o None si hay error
        """
        pass
    
    @abstractmethod
    def get_batch_quotes(self, symbol_codes: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Obtiene quotes para múltiples símbolos.
        
        Args:
            symbol_codes: Lista de códigos de símbolos
            
        Returns:
            Dict con símbolo como key y quote como value
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """Limpia recursos del provider."""
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el provider.
        
        Returns:
            Dict con información del provider
        """
        return {
            "name": self.__class__.__name__,
            "description": "Base data provider interface"
        }