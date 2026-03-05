# 🤝 Guía de Contribución

🇲🇽 **Español** | 🇺🇸 [English](#english)

¡Gracias por tu interés en contribuir a TacoTrader! Como buen taquero, valoramos a todos los que quieren ayudar a mejorar la receta. Esta guía te ayudará a contribuir de manera efectiva.

## 📋 Código de Conducta

Este proyecto y todos los participantes se rigen por el [Código de Conducta del Contribuyente](CODE_OF_CONDUCT.md). Al participar, se espera que respetes este código.

## 🚀 ¿Cómo Contribuir?

### 1. Reportar Bugs
- Usa el [issue tracker](https://github.com/tu-usuario/tacotrader/issues)
- Incluye un título descriptivo
- Describe los pasos para reproducir el bug
- Incluye información del entorno (Python version, SO, etc.)
- Si es posible, incluye logs o capturas de pantalla

### 2. Sugerir Mejoras
- Describe claramente la funcionalidad que propones
- Explica por qué sería útil
- Si es posible, incluye ejemplos de uso

### 3. Enviar Pull Requests
1. **Fork** el repositorio
2. **Crea una rama** para tu feature:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```
3. **Haz tus cambios** siguiendo las convenciones del proyecto
4. **Ejecuta las pruebas**:
   ```bash
   python -m pytest tests/
   ```
5. **Actualiza la documentación** si es necesario
6. **Envía el Pull Request**

## 🛠️ Configuración del Entorno de Desarrollo

```bash
# 1. Clona tu fork
git clone https://github.com/tu-usuario/tacotrader.git
cd tacotrader

# 2. Crea entorno virtual
python -m venv .venv

# 3. Activa entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Instala dependencias de desarrollo
pip install -r requirements-dev.txt
```

## 📝 Convenciones de Código

### Estilo de Código
- Seguimos [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Usamos **black** para formateo automático
- Usamos **isort** para ordenar imports
- Usamos **flake8** para linting

### Commits
- Usa mensajes de commit claros y descriptivos
- Sigue el formato: `tipo(scope): descripción`
- Tipos comunes: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Documentación
- Documenta funciones y clases con docstrings
- Actualiza el README si agregas nuevas funcionalidades
- Mantén los comentarios en español o inglés según el contexto

## 🧪 Testing

- Escribe pruebas para nuevas funcionalidades
- Mantén o mejora la cobertura de pruebas existentes
- Ejecuta todas las pruebas antes de enviar un PR:
  ```bash
  python -m pytest tests/ --cov=src --cov-report=term-missing
  ```

## 📚 Estructura del Proyecto

```
tacotrader/
├── src/                    # Código fuente principal
├── tests/                  # Pruebas unitarias
├── docs/                   # Documentación
├── config.example.yaml     # Configuración de ejemplo
├── requirements.txt        # Dependencias principales
├── requirements-dev.txt    # Dependencias de desarrollo
└── README.md              # Documentación principal
```

## 🎯 Prioridades del Proyecto

1. **Estabilidad**: El bot debe ser confiable y estable
2. **Seguridad**: Manejo seguro de credenciales y datos
3. **Rendimiento**: Ejecución eficiente y rápida
4. **Usabilidad**: Configuración y uso sencillos
5. **Documentación**: Documentación clara y completa

## ❓ ¿Necesitas Ayuda?

- Revisa la [documentación](README.md)
- Abre un [issue](https://github.com/tu-usuario/tacotrader/issues)
- Únete a nuestro [canal de Discord/Telegram] (si existe)

---

<a id="english"></a>
# 🤝 Contributing Guide

🇺🇸 **English** | 🇲🇽 [Español](#español)

Thank you for your interest in contributing to TacoTrader! Like a good taquero, we value everyone who wants to help improve the recipe. This guide will help you contribute effectively.

## 📋 Code of Conduct

This project and all participants are governed by the [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 🚀 How to Contribute?

### 1. Report Bugs
- Use the [issue tracker](https://github.com/your-username/tacotrader/issues)
- Include a descriptive title
- Describe steps to reproduce the bug
- Include environment information (Python version, OS, etc.)
- If possible, include logs or screenshots

### 2. Suggest Improvements
- Clearly describe the functionality you propose
- Explain why it would be useful
- If possible, include usage examples

### 3. Submit Pull Requests
1. **Fork** the repository
2. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/new-functionality
   ```
3. **Make your changes** following project conventions
4. **Run tests**:
   ```bash
   python -m pytest tests/
   ```
5. **Update documentation** if necessary
6. **Submit the Pull Request**

## 🛠️ Development Environment Setup

```bash
# 1. Clone your fork
git clone https://github.com/your-username/tacotrader.git
cd tacotrader

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Install development dependencies
pip install -r requirements-dev.txt
```

## 📝 Code Conventions

### Code Style
- We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- We use **black** for automatic formatting
- We use **isort** for import sorting
- We use **flake8** for linting

### Commits
- Use clear and descriptive commit messages
- Follow the format: `type(scope): description`
- Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Documentation
- Document functions and classes with docstrings
- Update README if you add new functionality
- Keep comments in Spanish or English according to context

## 🧪 Testing

- Write tests for new functionality
- Maintain or improve existing test coverage
- Run all tests before submitting a PR:
  ```bash
  python -m pytest tests/ --cov=src --cov-report=term-missing
  ```

## 📚 Project Structure

```
tacotrader/
├── src/                    # Main source code
├── tests/                  # Unit tests
├── docs/                   # Documentation
├── config.example.yaml     # Example configuration
├── requirements.txt        # Main dependencies
├── requirements-dev.txt    # Development dependencies
└── README.md              # Main documentation
```

## 🎯 Project Priorities

1. **Stability**: The bot must be reliable and stable
2. **Security**: Secure handling of credentials and data
3. **Performance**: Efficient and fast execution
4. **Usability**: Simple configuration and use
5. **Documentation**: Clear and complete documentation

## ❓ Need Help?

- Check the [documentation](README.md)
- Open an [issue](https://github.com/your-username/tacotrader/issues)
- Join our [Discord/Telegram channel] (if exists)