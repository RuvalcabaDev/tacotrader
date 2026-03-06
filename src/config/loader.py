import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import logger


class ConfigLoader:
    """
    Cargador de configuración para TacoTrader.
    
    Combina:
    1. Variables de entorno (.env)
    2. Archivo de configuración YAML
    3. Valores por defecto
    """
    
    def __init__(self, env_file: str = ".env", config_file: str = "config/config.yaml"):
        """
        Args:
            env_file: Ruta al archivo .env
            config_file: Ruta al archivo de configuración YAML
        """
        self.env_file = Path(env_file)
        self.config_file = Path(config_file)
        
        # Cargar variables de entorno
        self._load_env_vars()
        
        # Cargar configuración YAML
        self.config = self._load_yaml_config()
        
        # Validar configuración
        self._validate_config()
        
        logger.info("Configuración cargada exitosamente")
    
    def _load_env_vars(self) -> None:
        """Carga variables de entorno desde .env."""
        if self.env_file.exists():
            load_dotenv(self.env_file)
            logger.debug(f"Variables de entorno cargadas desde {self.env_file}")
        else:
            logger.warning(f"Archivo .env no encontrado: {self.env_file}")
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Carga configuración desde archivo YAML."""
        if not self.config_file.exists():
            logger.warning(f"Archivo de configuración no encontrado: {self.config_file}")
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            logger.debug(f"Configuración YAML cargada desde {self.config_file}")
            return config
            
        except Exception as e:
            logger.error(f"Error cargando configuración YAML: {e}")
            return {}
    
    def _validate_config(self) -> None:
        """Valida la configuración mínima requerida."""
        required_env_vars = [
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID',
            'ITICK_API_KEY'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Variables de entorno faltantes: {missing_vars}")
        
        # Validar configuración YAML mínima
        required_yaml_sections = ['market', 'screener']
        for section in required_yaml_sections:
            if section not in self.config:
                logger.warning(f"Sección de configuración YAML faltante: {section}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración.
        
        Prioridad:
        1. Variable de entorno (con prefijo)
        2. Configuración YAML (notación con puntos)
        3. Valor por defecto
        
        Args:
            key: Clave de configuración (ej: 'market.open_time' o 'TELEGRAM_BOT_TOKEN')
            default: Valor por defecto si no se encuentra
            
        Returns:
            Valor de configuración
        """
        # Primero intentar como variable de entorno
        env_value = os.getenv(key)
        if env_value is not None:
            # Intentar convertir tipos comunes
            if env_value.lower() in ('true', 'false'):
                return env_value.lower() == 'true'
            try:
                if '.' in env_value:
                    return float(env_value)
                return int(env_value)
            except ValueError:
                return env_value
        
        # Luego intentar en configuración YAML (notación con puntos)
        if '.' in key:
            parts = key.split('.')
            value = self.config
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            
            if value is not None:
                return value
        
        # Finalmente, buscar directamente en config YAML
        if key in self.config:
            return self.config[key]
        
        # Valor por defecto
        return default
    
    def get_market_config(self) -> Dict[str, Any]:
        """Obtiene configuración del mercado."""
        return self.config.get('market', {})
    
    def get_screener_config(self) -> Dict[str, Any]:
        """Obtiene configuración del screener."""
        return self.config.get('screener', {})
    
    def get_alerts_config(self) -> Dict[str, Any]:
        """Obtiene configuración de alertas."""
        return self.config.get('alerts', {})
    
    def get_data_providers_config(self) -> Dict[str, Any]:
        """Obtiene configuración de data providers."""
        return self.config.get('data_providers', {})
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Obtiene configuración de Telegram."""
        return {
            'bot_token': self.get('TELEGRAM_BOT_TOKEN'),
            'chat_id': self.get('TELEGRAM_CHAT_ID')
        }
    
    def get_itick_config(self) -> Dict[str, Any]:
        """Obtiene configuración de iTick."""
        return {
            'api_key': self.get('ITICK_API_KEY'),
            'base_url': self.get('ITICK_API_BASE_URL', 'https://api.itick.org')
        }
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obtiene toda la configuración combinada."""
        config = {
            'env': {
                'TELEGRAM_BOT_TOKEN': '***' if self.get('TELEGRAM_BOT_TOKEN') else None,
                'TELEGRAM_CHAT_ID': self.get('TELEGRAM_CHAT_ID'),
                'ITICK_API_KEY': '***' if self.get('ITICK_API_KEY') else None,
                'ITICK_API_BASE_URL': self.get('ITICK_API_BASE_URL'),
            },
            'yaml': self.config
        }
        
        return config


# Instancia global de configuración
config_loader = ConfigLoader()