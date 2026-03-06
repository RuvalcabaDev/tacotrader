# 🌮 TacoTrader

🇲🇽 **Español** | 🇺🇸 [English](#english)

## El bot que no se clava, se sirve.

TacoTrader no es otro bot aburrido de trading. Es tu compa algorítmico que, como buen taquero, sabe exactamente cuándo voltear el pastor, calentar la tortilla y servirlo calientito antes de que alguien más le pique.

Este bot ejecuta estrategias de trading automatizado con la precisión de un taquero de esquina: rápido, efectivo y sin vueltas. Analiza el mercado, detecta oportunidades y ejecuta órdenes mientras tú te echas un Sueño.

### ¿Qué lo hace diferente?

🌶️ **Picosito pero controlado**: Riesgo calculado, nada de irse de hocico.

🧅 **Bien servido**: Ejecuta trades completos, no medias porciones.

🔥 **Siempre caliente**: Reacciona al mercado en tiempo real, como si tuviera el comal bien puesto.

> "Del mercado a tu cartera, como de la taquiza a tu casa."

## 🚀 Características

- 📈 **Análisis de mercado** en tiempo real
- ⚡ **Ejecución rápida** de órdenes
- 🛡️ **Gestión de riesgo** inteligente
- 📊 **Monitoreo** continuo del portafolio
- 🔔 **Alertas** personalizadas

## 📦 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/RuvalcabaDev/tacotrader.git
cd tacotrader

# Crear entorno virtual (recomendado)
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## ⚙️ Configuración

1. Copia el archivo de configuración de ejemplo:
```bash
cp config.example.yaml config.yaml
```

2. Edita `config.yaml` con tus credenciales y preferencias:
```yaml
# Configuración básica
bot:
  name: "TacoTrader"
  version: "1.0.0"
  
# Configuración de trading
trading:
  risk_per_trade: 0.02  # 2% del capital por trade
  max_open_trades: 5
  
# Notificaciones
notifications:
  enabled: true
  telegram_token: "TU_TOKEN_AQUI"
  chat_id: "TU_CHAT_ID"
```

## 🎯 Uso

```bash
# Ejecutar el bot
python main.py

# Ejecutar en modo desarrollo
python main.py --debug

# Ver ayuda
python main.py --help
```

## 🧪 Testing

```bash
# Ejecutar pruebas unitarias
python -m pytest tests/

# Ejecutar pruebas con cobertura
python -m pytest --cov=src tests/
```

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre nuestro código de conducta y el proceso para enviar pull requests.

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👨‍💻 Autor

**Salvador Ruvalcaba** - [@RuvalcabaDev](https://github.com/RuvalcabaDev)

---

<a id="english"></a>
# 🌮 TacoTrader

🇺🇸 **English** | 🇲🇽 [Español](#español)

## The bot that doesn't get greedy, it just serves.

TacoTrader isn't just another boring trading bot. It's your algorithmic homie that, like a master taquero, knows exactly when to flip the pastor, warm up the tortilla, and serve it hot before anyone else grabs the opportunity.

This bot executes automated trading strategies with the precision of a street taquero: fast, effective, and straight to the point. It scans the market, spots opportunities, and executes orders while you take a well-deserved siesta.

### What makes it different?

🌶️ **Spicy but disciplined**: Calculated risk, no reckless moves.

🧅 **Full portions**: Executes complete trades, no half orders.

🔥 **Always hot**: Reacts to the market in real-time, like a grill that's always ready.

> "From the market to your wallet, like from the taquiza to your doorstep."

## 🚀 Features

- 📈 **Real-time market analysis**
- ⚡ **Fast order execution**
- 🛡️ **Intelligent risk management**
- 📊 **Continuous portfolio monitoring**
- 🔔 **Custom alerts**

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/RuvalcabaDev/tacotrader.git
cd tacotrader

# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

1. Copy the example configuration file:
```bash
cp config.example.yaml config.yaml
```

2. Edit `config.yaml` with your credentials and preferences:
```yaml
# Basic configuration
bot:
  name: "TacoTrader"
  version: "1.0.0"
  
# Trading configuration
trading:
  risk_per_trade: 0.02  # 2% of capital per trade
  max_open_trades: 5
  
# Notifications
notifications:
  enabled: true
  telegram_token: "YOUR_TOKEN_HERE"
  chat_id: "YOUR_CHAT_ID"
```

## 🎯 Usage

```bash
# Run the bot
python main.py

# Run in development mode
python main.py --debug

# Show help
python main.py --help
```

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/

# Run tests with coverage
python -m pytest --cov=src tests/
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Salvador Ruvalcaba** - [@RuvalcabaDev](https://github.com/RuvalcabaDev)