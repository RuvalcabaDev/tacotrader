# 🌮 TacoTrader BMV - Guía de Despliegue

## 📋 Requisitos Previos

### 1. **Python 3.13.11+**
```bash
python --version
```

### 2. **Docker y Docker Compose** (opcional, para contenedores)
```bash
docker --version
docker-compose --version
```

### 3. **Cuentas y Tokens**
- **iTick API**: Token gratuito (5 requests/minuto)
- **Telegram Bot**: Bot creado con @BotFather
- **Telegram Channel**: Canal para alertas

## 🚀 Despliegue Rápido

### Opción 1: Ejecución Directa (Python)

1. **Clonar repositorio**
```bash
git clone <repo-url>
cd tacotrader
```

2. **Configurar entorno**
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus tokens
nano .env  # o tu editor favorito
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Probar configuración**
```bash
python scripts/test_basic.py
```

5. **Ejecutar TacoTrader**
```bash
python main.py
```

### Opción 2: Docker

1. **Configurar entorno**
```bash
cp .env.example .env
# Editar .env
```

2. **Construir y ejecutar**
```bash
docker-compose up -d
```

3. **Ver logs**
```bash
docker-compose logs -f
```

## ⚙️ Configuración Detallada

### Archivo `.env`
```env
# Telegram Configuration (OBLIGATORIO)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=-

# iTick API Configuration (OBLIGATORIO)
ITICK_API_KEY=
ITICK_API_BASE_URL=https://api.itick.org

# BMV Market Hours (Horario extendido)
BMV_MARKET_OPEN_CDMX=07:00
BMV_MARKET_CLOSE_CDMX=15:00
BMV_SCRAPE_INTERVAL_MINUTES=10

# Screener Configuration
BMV_MAX_SYMBOLS=100
BMV_MIN_MOVEMENT_PERCENT=2.0
BMV_MIN_REL_VOLUME=1.8
BMV_MIN_ATR_PERCENT=2.5
BMV_MIN_MARKET_CAP_MXN=10000000000
BMV_MIN_PRICE_MXN=10.0

# Logging
LOG_LEVEL=INFO
```

### Archivo `config/config.yaml`
```yaml
# Configuración avanzada del screener
screener:
  max_symbols: 100
  top_results: 5
  
  criteria:
    min_movement_percent: 2.0
    min_relative_volume: 1.8
    min_atr_percent: 2.5
    min_market_cap_mxn: 10000000000
    min_price_mxn: 10.0
```

## 🔧 Comandos Útiles

### Desarrollo
```bash
# Ejecutar pruebas
python scripts/test_basic.py

# Ejecutar screener una vez (testing)
python -c "from src.core.tacotrader import TacoTraderBMV; t = TacoTraderBMV(); t.run_once()"

# Ver logs en tiempo real
tail -f logs/tacotrader.log
```

### Docker
```bash
# Construir imagen
docker-compose build

# Iniciar servicio
docker-compose up -d

# Detener servicio
docker-compose down

# Ver logs
docker-compose logs -f

# Ejecutar comandos dentro del contenedor
docker-compose exec tacotrader-bmv python scripts/test_basic.py
```

### Monitoreo
```bash
# Ver estado del scheduler
curl http://localhost:8080/status  # Si se implementa API

# Ver métricas
cat data/bmv_symbols.json | jq '.metadata'

# Ver rate limit status
grep "Rate limit" logs/tacotrader.log | tail -5
```

## 📊 Estructura del Proyecto

```
tacotrader/
├── src/                    # Código fuente
│   ├── core/              # Lógica principal
│   ├── data/              # Data providers
│   ├── screener/          # Análisis de mercado
│   ├── alerts/            # Sistema de alertas
│   ├── scheduler/         # Programación de tareas
│   ├── config/            # Configuración
│   └── utils/             # Utilidades
├── config/                # Archivos de configuración
├── data/                  # Datos persistentes
├── logs/                  # Logs de aplicación
├── scripts/               # Scripts de utilidad
├── .env                   # Variables de entorno
├── requirements.txt       # Dependencias Python
├── Dockerfile            # Configuración Docker
└── docker-compose.yml    # Orquestación Docker
```

## 🚨 Solución de Problemas

### Problema: "Missing API key in request"
**Solución**: Verifica que el token de iTick esté correcto en `.env`

### Problema: "Bot token is invalid"
**Solución**: 
1. Crear nuevo bot con @BotFather
2. Obtener nuevo token
3. Actualizar `.env`

### Problema: Rate limiting frecuente
**Solución**:
- La capa gratuita de iTick es 5 requests/minuto
- El bot está diseñado para respetar este límite
- Considera upgrade a plan pagado para más requests

### Problema: No se envían alertas
**Solución**:
1. Verificar que el bot esté agregado al canal
2. Verificar permisos del bot en el canal
3. Revisar logs para errores de Telegram API

## 🔄 Actualización

### Actualizar código
```bash
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

### Actualizar dependencias
```bash
pip install -r requirements.txt --upgrade
# o
docker-compose build --no-cache
```

## 📈 Monitoreo y Métricas

### Logs importantes a monitorear
```bash
# Alertas enviadas
grep "Alerta enviada" logs/tacotrader.log

# Errores
grep "ERROR" logs/tacotrader.log

# Rate limiting
grep "Rate limit" logs/tacotrader.log

# Estado del mercado
grep "Mercado" logs/tacotrader.log
```

### Métricas clave
- **Símbolos analizados**: Por ejecución
- **Oportunidades encontradas**: Por ejecución
- **Alertas enviadas**: Por día
- **Rate limit utilizado**: Por minuto
- **Uptime**: Tiempo de ejecución

## 🔒 Seguridad

### Tokens y Credenciales
- **NUNCA** commits tokens en git
- Usar `.env` para secrets
- `.env` está en `.gitignore`
- Rotar tokens periódicamente

### Permisos
```bash
# Archivos sensibles
chmod 600 .env
chmod 700 config/

# Directorios de datos
chmod 755 data/ logs/
```

## 🆘 Soporte

### Recursos
- **Documentación iTick**: https://itick.org
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Issues**: [Repositorio GitHub]

### Comandos de diagnóstico
```bash
# Verificar conexión iTick
curl -H "token: $ITICK_API_KEY" "https://api.itick.org/symbol/list?type=stock&region=MX"

# Verificar bot de Telegram
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"

# Verificar estado del sistema
python scripts/test_basic.py
```

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.