# Manual de Despliegue — MediPrior

## Prerequisitos

- Python 3.10
- Node.js 18+
- AWS CLI configurado
- Serverless Framework v4+
- Cuenta en Groq: https://console.groq.com/keys

## 1. Clonar el repositorio

```bash
git clone https://github.com/alexaliaga16/Mediprior_Hackaton_cloud.git
cd Mediprior_Hackaton_cloud
```

## 2. Configurar credenciales AWS

Obtener credenciales desde AWS Academy (Vocareum):
- Click en "AWS Details" → "Show"
- Copiar el bloque completo

```bash
nano ~/.aws/credentials
# Pegar el bloque de credenciales
```

## 3. Configurar Groq API Key

Obtener key en https://console.groq.com/keys

```bash
export GROQ_API_KEY=tu_groq_api_key
```

## 4. Deploy del backend (1 solo comando)

```bash
cd backend
serverless deploy
```

El deploy retorna las URLs del API Gateway:
```
POST https://{id}.execute-api.us-east-1.amazonaws.com/upload
GET  https://{id}.execute-api.us-east-1.amazonaws.com/results/{jobId}
POST https://{id}.execute-api.us-east-1.amazonaws.com/retry-failed
```

Serverless Framework crea automáticamente:
- Lambda ingester
- Lambda processor
- Lambda getter
- Lambda retrier
- SQS Main Queue
- SQS Dead Letter Queue (DLQ)
- DynamoDB tabla Jobs
- DynamoDB tabla Patients
- API Gateway

## 5. Deploy del frontend

### Opción A: AWS Amplify (recomendado)

1. Ir a AWS Amplify en la consola de AWS
2. Click en "Crear nueva aplicación"
3. Seleccionar GitHub → autorizar → elegir repo `Mediprior_Hackaton_cloud`
4. Seleccionar rama `main`
5. Configurar build:
   - Comando: `cd frontend && npm install && npm run build`
   - Directorio de salida: `frontend/dist`
6. Click en "Guardar e implementar"

URL pública: `https://main.d1x79kqokvl757.amplifyapp.com`

### Opción B: S3 (alternativa)

```bash
cd frontend
npm install
npm run build

# Crear bucket S3
aws s3 mb s3://mediprior-frontend

# Desbloquear acceso público
aws s3api put-public-access-block \
  --bucket mediprior-frontend \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Aplicar política pública
aws s3api put-bucket-policy --bucket mediprior-frontend --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::mediprior-frontend/*"
  }]
}'

# Subir archivos
aws s3 sync dist/ s3://mediprior-frontend

# Habilitar website hosting
aws s3 website s3://mediprior-frontend \
  --index-document index.html \
  --error-document index.html
```

URL pública: `http://mediprior-frontend.s3-website-us-east-1.amazonaws.com`

## 6. Probar el sistema

1. Abrir la URL del frontend
2. Descargar la plantilla de ejemplo o usar `sample-data/pacientes_ejemplo.csv`
3. Subir el CSV desde el frontend
4. Esperar 60-90 segundos para 25 pacientes
5. Ver resultados priorizados por urgencia con colores
6. Si hay pacientes fallidos, usar el botón "Reintentar pacientes fallidos"

## 7. Endpoints disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /upload | Subir CSV de pacientes |
| GET | /results/{jobId} | Obtener resultados del job |
| POST | /retry-failed | Reprocesar pacientes de la DLQ |

## Notas importantes

- Las credenciales de AWS Academy expiran cada 4 horas
- Al expirar, renovar en Vocareum y volver al paso 2
- La GROQ_API_KEY se debe exportar antes de cada `serverless deploy`
- El sistema soporta máximo 30 pacientes por batch
- El backend es 100% serverless — no hay servidores que administrar
- Serverless Framework despliega toda la infraestructura en 1 comando