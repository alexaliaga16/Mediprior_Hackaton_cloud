# Pruebas E2E locales

Pasos para ejecutar el flujo completo localmente usando LocalStack:

1. Levantar LocalStack (requiere Docker):

```bash
docker compose -f docker-compose.localstack.yml up -d
```

2. Instalar dependencias Python necesarias (puedes usar un virtualenv):

```bash
pip install boto3
```

3. Ejecutar el script de prueba E2E:

```bash
python backend/local/run_local_e2e.py
```

El script creará las tablas y colas en LocalStack, llamará al `ingester` con el CSV de ejemplo,
procesará los mensajes en SQS invocando `processor` (con un stub de Groq) y finalmente
llamará a `getter` para mostrar los resultados.

Notas:
- El script parchea la importación de `groq` para no requerir credenciales externas.
- Si quieres probar el `processor` con la API real de Groq, instala la librería y configura `GROQ_API_KEY`.
- Asegúrate de que `LOCALSTACK_ENDPOINT` apunte a `http://localhost:4566` si cambias puertos.
