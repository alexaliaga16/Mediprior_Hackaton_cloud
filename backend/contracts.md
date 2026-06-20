# Jobs Table

PK: jobId

{
  "jobId": "abc-123",
  "totalPatients": 25,
  "processedPatients": 0,
  "status": "CREATING",
  "timestamp": "2026-06-19T10:00:00Z"
}

# Patients Table

PK: jobId
SK: patientId

{
  "jobId": "abc-123",
  "patientId": "uuid",
  "nombre": "Juan Pérez",
  "sintomas": "dolor de pecho",
  "urgencia": "CRITICO",
  "riesgo": 92,
  "especialidad": "Cardiología",
  "alerta": "Posible IAM",
  "recomendacion": "Atención inmediata",
  "justificacion": "...",
  "status": "DONE",
  "timestamp": "2026-06-19T10:00:00Z"
}