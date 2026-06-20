# MediPrior — Sistema de Priorización Clínica Asistida por IA

> Hackathon UTEC · AWS + Groq · Junio 2026

Sistema que permite a técnicos de salud en postas rurales del Perú subir una lista de pacientes en texto libre y recibir en segundos una priorización clínica asistida por IA, ordenada por nivel de urgencia.

---

## El problema

En el Perú existen más de 7.000 postas médicas rurales donde un solo técnico atiende decenas de pacientes diarios sin apoyo especializado. La priorización se hace manualmente y de forma subjetiva, generando riesgo de muerte por atención tardía en casos críticos.

**¿Por qué un LLM y no ML tradicional?**

```
Técnico escribe texto libre:
"el señor llegó con el pecho apretado,
sudando frío y con el brazo izquierdo
adormecido desde hace 20 minutos"

ML tradicional → necesita dataset etiquetado, features estructuradas,
                 meses de entrenamiento, no entiende español coloquial

Groq LLM      → CRÍTICO | Cardiología | Riesgo 92%
                 Posible IAM — Atención inmediata, EKG urgente
```

---

## Arquitectura

```
[Usuario]
    │ sube CSV (nombre, sintomas)
    ▼
[Frontend React — S3 / Amplify]
    │ POST /upload
    ▼
[API Gateway → Lambda INGESTER]
    │ 1. Crea Job  { status: CREATING }
    │ 2. Envía 1 mensaje SQS por paciente
    │ 3. Actualiza Job { status: PROCESSING }
    │ 4. Retorna jobId al frontend
    │
    ├──────────────────────────────┐
    ▼                              ▼
[DynamoDB: Jobs]          [SQS Main Queue]
                          visibilityTimeout: 120s
                          maxReceiveCount: 3
                                   │ trigger (batchSize: 1)
                                   ▼
                          [Lambda PROCESSOR]
                           1. Llama Groq API (llama-3.3-70b)
                           2. Guarda urgencia, riesgo,
                              especialidad, alerta,
                              recomendacion, justificacion
                           3. processedPatients += 1 (atómico)
                           4. Si processed == total → COMPLETED
                           Si falla 3x → [SQS DLQ]
                                   │
                     ┌─────────────┴──────────────┐
                     ▼                            ▼
              [DynamoDB: Jobs]          [DynamoDB: Patients]

[Frontend polling cada 3s]
    │ GET /results/{jobId}
    ▼
[Lambda GETTER]
    retorna Job + Patients + Metrics

[Botón "Reintentar fallidos"]
    │ POST /retry-failed
    ▼
[Lambda RETRIER]
    mueve mensajes de DLQ → Main Queue
```

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite, deployado en AWS Amplify / S3 |
| Backend | AWS Lambda (Python 3.10) × 4 funciones |
| IaC | Serverless Framework v4 |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Cola | AWS SQS + Dead Letter Queue |
| Base de datos | AWS DynamoDB (2 tablas) |
| API | AWS API Gateway (HTTP API) |

---

## Estructura del repositorio

```
mediprior/
├── backend/
│   ├── serverless.yml          # infraestructura completa como código
│   ├── requirements.txt        # groq, boto3
│   └── functions/
│       ├── ingester.py         # POST /upload — parsea CSV, crea job, encola
│       ├── processor.py        # trigger SQS — llama Groq, guarda resultado
│       ├── getter.py           # GET /results/{jobId} — devuelve progreso
│       └── retrier.py          # POST /retry-failed — mueve DLQ → Main Queue
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # estado global, upload, polling
│   │   └── components/
│   │       ├── UploadCSV.jsx   # drag & drop + descarga de plantilla
│   │       ├── ProgressBar.jsx # barra de progreso processedPatients/total
│   │       ├── MetricsDashboard.jsx  # conteo críticos/moderados/leves
│   │       ├── ResultsTable.jsx      # cards por paciente ordenados por riesgo
│   │       └── RetryButton.jsx       # reintenta pacientes FAILED vía DLQ
│   ├── .env.example
│   └── deploy.sh
├── sample-data/
│   └── pacientes_ejemplo.csv   # 25 pacientes de prueba
└── docs/
    └── manual.md               # guía de despliegue paso a paso
```

---

## API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/upload` | Recibe CSV multipart, crea job, retorna `jobId` |
| `GET` | `/results/{jobId}` | Retorna job, lista de pacientes y métricas |
| `POST` | `/retry-failed` | Mueve mensajes de la DLQ a la cola principal |

**POST /upload — respuesta:**
```json
{ "jobId": "uuid", "totalPatients": 25, "status": "PROCESSING" }
```

**GET /results/{jobId} — respuesta:**
```json
{
  "job": {
    "jobId": "...",
    "totalPatients": 25,
    "processedPatients": 18,
    "status": "PROCESSING | COMPLETED"
  },
  "metrics": { "critical": 4, "moderate": 9, "mild": 12 },
  "patients": [
    {
      "nombre": "Juan Perez",
      "urgencia": "CRITICO | MODERADO | LEVE",
      "riesgo": 90,
      "especialidad": "Cardiologia",
      "alerta": "Posible infarto de miocardio",
      "recomendacion": "Atencion inmediata",
      "justificacion": "...",
      "status": "DONE | PENDING | FAILED"
    }
  ]
}
```

**Formato del CSV:**
```csv
nombre,sintomas
Juan Pérez,"el señor llegó con el pecho apretado, sudando frío"
María García,"dolor intenso de cabeza, visión borrosa"
```
Máximo 30 pacientes por batch.

---

## Flujo de estados

```
Job:      CREATING → PROCESSING → COMPLETED
                               → FAILED (si SQS falla en ingester)

Paciente: PENDING → DONE
                  → FAILED (si Groq falla 3 veces → va a DLQ)
```

---

## Despliegue

### Prerequisitos

- Python 3.10+
- Node.js 18+
- AWS CLI configurado
- Serverless Framework v4: `npm i -g serverless`
- API Key de Groq: [console.groq.com/keys](https://console.groq.com/keys)

### 1. Clonar

```bash
git clone https://github.com/alexaliaga16/Mediprior_Hackaton_cloud.git
cd Mediprior_Hackaton_cloud
```

### 2. Credenciales AWS

```bash
# Pegar credenciales de AWS Academy (Vocareum → AWS Details → Show)
nano ~/.aws/credentials
```

### 3. Backend — 1 comando

```bash
cd backend
export GROQ_API_KEY=tu_groq_api_key
serverless deploy
```

Serverless crea automáticamente: 4 Lambdas, SQS + DLQ, 2 tablas DynamoDB y el API Gateway.
Al finalizar imprime las URLs de los endpoints.

### 4. Frontend

Copiar la URL base del API Gateway al archivo de entorno:

```bash
cd frontend
cp .env.example .env
# Editar .env y poner VITE_API_BASE_URL=https://{id}.execute-api.us-east-1.amazonaws.com
```

**Opción A — AWS Amplify (recomendado):**

1. Ir a AWS Amplify → Crear nueva aplicación → GitHub
2. Seleccionar repo `Mediprior_Hackaton_cloud`, rama `main`
3. Build: comando `cd frontend && npm install && npm run build`, salida `frontend/dist`
4. Agregar variable de entorno `VITE_API_BASE_URL`
5. Guardar e implementar

**Opción B — S3:**

```bash
npm install && npm run build
aws s3 mb s3://mediprior-frontend
aws s3 sync dist/ s3://mediprior-frontend
aws s3 website s3://mediprior-frontend --index-document index.html --error-document index.html
```

### 5. Probar

1. Abrir la URL del frontend
2. Subir `sample-data/pacientes_ejemplo.csv` (o descargar la plantilla desde la app)
3. Esperar ~60-90 segundos para 25 pacientes
4. Ver resultados ordenados por urgencia con colores rojo / amarillo / verde
5. Si hay pacientes fallidos, usar el botón **Reintentar pacientes fallidos**

---

## Resiliencia

| Riesgo | Solución |
|--------|----------|
| Groq rate limit (429) | SQS reintenta automático con `visibilityTimeout` |
| Groq timeout | SQS reintenta automático |
| Falla 3 veces consecutivas | Mensaje va a DLQ — nunca se pierde |
| Actualizaciones concurrentes en DynamoDB | `UpdateItem` atómico (`processedPatients += 1`) |
| Error en ingester (SQS falla) | Job queda en `FAILED` — error visible al usuario |
| Pacientes FAILED en DLQ | Botón "Reintentar" los remueve a la cola principal |

---

## Disclaimer ético

```
El sistema NO diagnostica enfermedades.
El sistema NO prescribe tratamientos.
El sistema NO reemplaza médicos ni profesionales de salud.
El sistema ÚNICAMENTE prioriza pacientes para atención temprana.
La decisión final SIEMPRE es del profesional de salud.
```

---

## Equipo

Desarrollado para el Hackathon UTEC — Computación en la Nube · Junio 2026
