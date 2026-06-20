Acá va todo. El documento completo del proyecto.

---

# MediPrior — Sistema de Priorización Clínica Asistida por IA

---

## 1. Contexto de la Problemática

**Problema real:**
En el Perú existen más de 7,000 postas médicas rurales donde un solo técnico de salud atiende decenas de pacientes diarios sin apoyo médico especializado. La priorización de atención se hace manualmente y de forma subjetiva, generando riesgo de muerte por atención tardía en casos críticos.

**Por qué LLM y no ML tradicional:**
```
Técnico escribe texto libre:
"el señor llegó con el pecho apretado,
sudando frío y con el brazo izquierdo
adormecido desde hace 20 minutos"

→ ML tradicional: necesita dataset etiquetado enorme
                  necesita features estructuradas
                  meses de entrenamiento
                  no entiende español coloquial

→ Groq LLM:       CRÍTICO | Cardiología | Riesgo 92%
                  Posible IAM
                  Atención inmediata, EKG urgente
```

**Casos de uso:**
1. Posta rural procesa 25 fichas simultáneas en campaña de salud
2. Hospital distrital filtra casos urgentes de lista de espera masiva
3. Sistema de telemedicina pre-filtra pacientes antes de consulta remota

**Impacto esperado:**
Reducir el tiempo de identificación de casos críticos de minutos a segundos, permitiendo que el técnico de salud priorice correctamente bajo alta carga de pacientes.

**Framing ético — IMPORTANTE:**
```
El sistema NO diagnostica enfermedades
El sistema NO prescribe tratamientos
El sistema NO reemplaza médicos
El sistema ÚNICAMENTE prioriza pacientes para atención temprana
La decisión final SIEMPRE es del profesional de salud
```

**Por qué Groq:**
Groq fue elegido por su baja latencia y alta capacidad de procesamiento para cargas concurrentes, permitiendo analizar múltiples pacientes en paralelo con tiempos de respuesta reducidos vs otras APIs de LLM.

---

## 2. Stack Tecnológico

```
Cloud:      AWS (100%)
IaC:        Serverless Framework (org: potoncito)
LLM:        Groq API (llama-3.3-70b-versatile)
Queue:      SQS + DLQ
Database:   DynamoDB (2 tablas)
Functions:  Lambda Python 3.11
Frontend:   React + Vite
Hosting:    S3 + CloudFront
```

---

## 3. Arquitectura Completa

```
[Usuario]
    │
    │ sube CSV con 25 pacientes
    ▼
[Frontend React — S3 + CloudFront]
    │
    │ POST /upload
    ▼
[API Gateway]
    │
    ▼
[Lambda INGESTER]
    │ 1. Crear Job { status: CREATING, processedPatients: 0 }
    │ 2. Enviar 1 mensaje por paciente a SQS
    │ 3. Si algún envío falla → Job { status: FAILED } → error
    │ 4. Si todos ok → Job { status: PROCESSING } → retorna jobId
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
[DynamoDB Jobs]                      [SQS Main Queue]
                                      visibilityTimeout: 30s
                                      maxReceiveCount: 3
                                           │
                                           │ trigger batch=1
                                           ▼
                                    [Lambda PROCESSOR]
                                      │ 1. Recibe mensaje
                                      │ 2. Llama Groq API
                                      │ 3. Guarda en Patients
                                      │ 4. processedPatients += 1 (atómico)
                                      │ 5. Si processed==total → COMPLETED
                                      │
                                      ├── Si Groq falla → SQS reintenta
                                      └── Si falla 3x   → DLQ
                                           │
                              ┌────────────┴────────────┐
                              ▼                         ▼
                        [DynamoDB Jobs]          [DynamoDB Patients]
                        actualiza progreso       guarda resultado
                              │
                              ▼
                        [Lambda GETTER]
                        GET /results/{jobId}
                        retorna Job + Patients
                              │
                              ▼
                        [Frontend polling cada 3s]
                        muestra progreso + tabla
```

---

## 4. Flujo de Estados

```
Job:
CREATING → PROCESSING → COMPLETED
                     → FAILED (si SQS falla)

Patient:
PENDING → DONE
        → FAILED (si Groq falla 3x → va a DLQ)
```

---

## 5. Contrato de Datos

```json
// Tabla: Jobs
// PK: jobId
{
  "jobId":             "abc-123",
  "totalPatients":     25,
  "processedPatients": 0,
  "status":            "CREATING | PROCESSING | COMPLETED | FAILED",
  "timestamp":         "2026-06-19T10:00:00Z"
}

// Tabla: Patients
// PK: jobId | SK: patientId
{
  "jobId":         "abc-123",
  "patientId":     "uuid",
  "nombre":        "Juan Pérez",
  "sintomas":      "dolor de pecho, sudor frío...",
  "urgencia":      "CRÍTICO | MODERADO | LEVE",
  "riesgo":        92,
  "especialidad":  "Cardiología",
  "alerta":        "Posible IAM",
  "recomendacion": "Atención inmediata, EKG urgente",
  "justificacion": "Dolor torácico + sudor frío + adormecimiento brazo izquierdo = evento cardiovascular agudo",
  "status":        "PENDING | DONE | FAILED",
  "timestamp":     "2026-06-19T10:00:00Z"
}
```

---

## 6. Prompt al LLM (JSON estricto)

```
Eres un asistente de priorización clínica para postas médicas rurales del Perú.
NO diagnosticas enfermedades. ÚNICAMENTE priorizas pacientes.

Dado el siguiente reporte de síntomas en texto libre, responde ÚNICAMENTE
con JSON válido, sin texto adicional, sin markdown, sin explicaciones.

Síntomas: {sintomas}

Responde exactamente con esta estructura:
{
  "urgencia":      "CRÍTICO | MODERADO | LEVE",
  "riesgo":        0-100,
  "especialidad":  "nombre de especialidad médica",
  "alerta":        "diagnóstico presuntivo breve",
  "recomendacion": "acción inmediata recomendada",
  "justificacion": "explicación clínica breve de por qué esta prioridad"
}
```

---

## 7. División de Trabajo

```
Alexander (tú)
→ Lambda ingester (Python)
→ Lambda processor (Python)
→ Groq API integration
→ SQS + DLQ config en serverless.yml

Compañero 2
→ Lambda getter (Python)
→ DynamoDB tables config
→ API Gateway endpoints
→ Update atómico en DynamoDB

Compañero 3
→ Frontend React + Vite
→ Upload CSV component
→ Polling cada 3s
→ Dashboard: progreso + tabla + métricas
→ Deploy S3 + CloudFront
```

---

## 8. Variables de Entorno

```
GROQ_API_KEY         → Lambda processor (solo)
SQS_QUEUE_URL        → Lambda ingester
JOBS_TABLE           → Lambda ingester + processor + getter
PATIENTS_TABLE       → Lambda processor + getter
```

---

## 9. Estructura del Repositorio

```
mediprior/
├── backend/
│   ├── serverless.yml
│   ├── functions/
│   │   ├── ingester.py
│   │   ├── processor.py
│   │   └── getter.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── UploadCSV.jsx
│   │       ├── ProgressBar.jsx
│   │       └── ResultsTable.jsx
│   └── deploy.sh
├── docs/
│   ├── arquitectura.png
│   └── manual.md
├── sample-data/
│   └── pacientes_ejemplo.csv
└── README.md
```

---

## 10. Dashboard Frontend

```
┌─────────────────────────────────────────┐
│  MediPrior — Priorización Clínica IA   │
├─────────────────────────────────────────┤
│  [Subir CSV]  Procesando 18/25 (72%)   │
│  ████████████████░░░░░░░░               │
├──────┬──────────────────────────────────┤
│ 🔴 4 │ Críticos                        │
│ 🟡 9 │ Moderados                       │
│ 🟢12 │ Leves                           │
├──────┴──────────────────────────────────┤
│ Nombre  │Urgencia│Riesgo│Especialidad  │
│ Juan P. │🔴CRÍTICO│ 92% │Cardiología  │
│ María L.│🟡MODER │ 54% │Medicina Gral│
│ Pedro R.│🟢LEVE  │ 12% │Medicina Gral│
└─────────────────────────────────────────┘
```

---

## 11. Resiliencia — Por qué sacamos 4/4 en criterio 3

```
Riesgo                    → Solución
─────────────────────────────────────────────
Groq rate limit (429)     → SQS reintenta automático (visibilityTimeout)
Groq timeout              → SQS reintenta automático
Falla 3 veces             → DLQ — nunca se pierde data
2 Lambdas actualizan jobs → UpdateItem atómico en DynamoDB
SQS falla en ingester     → Job queda en FAILED — error claro al usuario
```