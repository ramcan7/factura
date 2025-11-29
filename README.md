# 💬 Agente Facturio para facturas.
### How to run it on your own machine

1️⃣ Instalar Docker y preparar el entorno
1. Instalar Docker Desktop

Windows / Mac / Linux

Descargar desde: https://www.docker.com/products/docker-desktop/

Instalar con la configuración por defecto.


2️⃣ Levantar el proyecto con Docker Compose
📁 Asegúrate que en tu carpeta del proyecto exista:
docker-compose.yml
app/
   ├─ main.py
   ├─ agent.py
   ├─ pdf_generator.py
   └─ requirements.txt

▶️ Para levantar el servicio:

Abre una terminal dentro del directorio del proyecto:

docker compose up --build


➡️ El agente Facturio está listo.

Ahora puedes enviar un pedido de factura

El Agente Facturio recibe lenguaje natural, pero requiere que el contenido incluya la información mínima del formato de una factura/boleta SUNAT, tal como:

Ejemplo:

Boleta de Venta electrónica Ferretería Carlos,
Dirección Av. Arequipa 500 Lima,
RUC 20111945860.
Fecha 2024-12-30.
Cliente: Juan Perez, DNI 45454545, Dirección Calle 1 Los Olivos.
Item: Martillo Precio: 20 soles. Cantidad 1


✉️ Información del proyecto 

Presentación: https://gamma.app/docs/Agente-de-Facturacion-SUNAT-Simplificando-el-Proceso-byyuako5ro16ban

Notion (Documentación/Prompts): https://www.notion.so/NTT-Data-2ba9eb61dca380e78745d48616d6a6b4?source=copy_link




### Evidencia - Prompts:







### Estructura
/
├── main.py              # Punto de entrada de la API (FastAPI) y definición de endpoints
├── gemini_handler.py    # Módulo de Inteligencia Artificial (Conexión con Google Gemini)
├── funciones.py         # Motor lógico: Cálculos matemáticos (IGV) y Generación de PDF
├── requirements.txt     # Lista de dependencias del proyecto
├── Dockerfile           # Configuración para construir la imagen del contenedor
├── docker-compose.yml   # Orquestación del servicio (para levantar la API fácilmente)
└── .gitignore           # Archivos ignorados por Git