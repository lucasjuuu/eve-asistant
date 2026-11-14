# IVI — Asistente de Inteligencia Artificial para Windows

**IVI** es un asistente personal de escritorio inspirado en los sistemas de Iron Man (JARVIS / FRIDAY).  
Incluye cerebro de OpenAI, voz con ElevenLabs, **memoria con RAG** (Retrieval-Augmented Generation), recordatorios y una interfaz moderna.

## Características

- **Cerebro**: OpenAI (modelos configurables). Mantiene contexto de conversación.
- **Memoria RAG**: Guarda recuerdos del usuario, genera embeddings y recupera solo los relevantes en cada consulta. No inventa información.
- **Voz**:
  - Entrada: micrófono + reconocimiento de voz (SpeechRecognition).
  - Salida: ElevenLabs (voz femenina configurable).
- **Recordatorios**: Persistentes. Se notifican mientras la aplicación esté abierta.
- **Seguridad**: Las API keys se guardan en **Windows Credential Manager** (nunca en texto plano ni en el ejecutable).
- **Interfaz**: PySide6, tema oscuro tecnológico.

## Requisitos

- Windows 10/11
- Python 3.10+ (solo para desarrollo)
- API key de [OpenAI](https://platform.openai.com/)
- API key de [ElevenLabs](https://elevenlabs.io/) (opcional, para voz)

## Instalación para desarrollo

```bash
git clone <tu-repositorio>
cd ivi
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

> **Nota sobre PyAudio**: en Windows puede requerir un wheel específico.  
> Si falla la instalación, descarga el wheel compatible desde  
> https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio e instálalo con `pip install <archivo.whl>`.

## Configuración

1. Abre **Archivo → Configuración**.
2. Introduce tu API key de OpenAI (se guarda de forma segura).
3. (Opcional) Introduce API key y Voice ID de ElevenLabs.
4. Ajusta modelo, temperatura, top-k de RAG y umbral de similitud.

La primera vez que guardes un recuerdo se generarán embeddings (consume tokens de OpenAI).

## Uso de la memoria RAG

- Desde el panel **Memoria** puedes añadir, ver y eliminar recuerdos manualmente.
- También puedes decir frases como «Recuerda que mi cumpleaños es el 15 de marzo» y IVI las guardará automáticamente.
- En cada mensaje, IVI busca los recuerdos más similares (similitud coseno) y los inyecta en el contexto del modelo.
- Puedes desactivar la memoria completamente en Configuración.

## Recordatorios

- Crea recordatorios desde el panel correspondiente.
- **Importante**: solo se notifican mientras IVI esté en ejecución.  
  Si cierras la aplicación, los recordatorios se conservan en disco y se evaluarán al volver a abrirla.

## Generar el ejecutable (IVI.exe)

### Opción A — GitHub Actions (recomendado)

1. Sube el proyecto a un repositorio de GitHub.
2. Ve a la pestaña **Actions**.
3. Ejecuta el workflow **Build IVI for Windows** (o espera a que se dispare con un push a `main`).
4. Al terminar, descarga el artefacto **IVI-Windows** (contiene `IVI.exe`) o el ZIP.

### Opción B — Compilación local en Windows

```bash
pip install pyinstaller
pyinstaller build/ivi.spec --noconfirm --clean
```

El ejecutable aparecerá en `dist/IVI.exe`.

## Estructura del proyecto

```
ivi/
├── main.py
├── requirements.txt
├── README.md
├── .github/workflows/build.yml
├── build/ivi.spec
├── assets/
└── ivi/
    ├── app.py
    ├── config.py
    ├── security.py
    ├── ai/
    ├── voice/
    ├── memory/          ← RAG (store.py)
    ├── reminders/
    ├── ui/
    └── utils/
```

## Privacidad y seguridad

- Las API keys **nunca** se escriben en el código fuente ni en archivos de configuración en texto plano.
- Se usan a través de `keyring` → Windows Credential Manager.
- Los recuerdos y recordatorios se guardan en `%APPDATA%\IVI\`.
- No se envían datos a ningún servidor propio; solo a OpenAI y ElevenLabs según las keys del usuario.

## Licencia

Uso personal y educativo. Asegúrate de cumplir los términos de OpenAI y ElevenLabs.

---

**IVI está lista.** Configura tus claves y comienza a conversar.

## Control del sistema y WhatsApp

IVI puede ejecutar acciones reales en tu PC mediante **function calling**:

### Ejemplos de órdenes

- «Abre la calculadora y calcula 2 + 2»
- «Abre el Bloc de notas»
- «Abre Chrome»
- «Escribe hola mundo» (en la ventana activa)
- «Presiona Ctrl+S»
- «Envía un WhatsApp al +54 9 11 1234-5678 diciendo que llego en 10 minutos»

### Seguridad

- Por defecto **cada acción pide confirmación** en un diálogo.
- Puedes desactivar la confirmación en configuración (no recomendado).
- Comandos de shell peligrosos están bloqueados.
- WhatsApp usa tu sesión de WhatsApp Web (debes haber iniciado sesión previamente).

### Dependencias extra

```bash
pip install pyautogui pyperclip pywhatkit Pillow
```

Para WhatsApp: la primera vez se abrirá el navegador en web.whatsapp.com.  
Escanea el código QR con tu teléfono si aún no tienes sesión.

