# MediPrior Frontend

Interfaz web para el sistema de priorización clínica asistida por IA.

## Instalación

```bash
npm install
```

## Desarrollo

```bash
npm run dev
```

La aplicación se abrirá en `http://localhost:3000`

## Variables de entorno

Crear un archivo `.env` basado en `.env.example`:

```bash
VITE_API_BASE_URL=https://your-api-endpoint.execute-api.us-east-1.amazonaws.com/dev
```

## Build para producción

```bash
npm run build
npm run preview
```

## Estructura del proyecto

```
src/
  ├── App.jsx              # Componente principal
  ├── App.css              # Estilos del app
  ├── main.jsx             # Punto de entrada
  ├── index.css            # Estilos globales
  ├── utils.js             # Funciones auxiliares
  └── components/
      ├── UploadCSV.jsx    # Carga de archivo CSV
      ├── UploadCSV.css
      ├── ProgressBar.jsx  # Barra de progreso
      ├── ProgressBar.css
      ├── ResultsTable.jsx # Tabla de resultados
      └── ResultsTable.css
```

## Flujo de la aplicación

1. **Upload**: Usuario carga un archivo CSV con pacientes
2. **Processing**: Sistema procesa los pacientes en paralelo
3. **Results**: Tabla con pacientes priorizados por urgencia

### Formato del CSV

```csv
nombre,sintomas
Juan Pérez,"el señor llegó con el pecho apretado, sudando frío"
María García,"dolor intenso de cabeza, visión borrosa"
```

## API Endpoints esperados

- `POST /upload` - Cargar archivo CSV
  - Retorna: `{ jobId, totalPatients }`

- `GET /results/{jobId}` - Obtener resultados
  - Retorna: `{ job: { status, processedPatients, totalPatients }, patients: [...] }`

## Notas importantes

- El sistema **NO diagnostica** enfermedades
- El sistema **NO prescribe** tratamientos
- La decisión final **siempre es del profesional de salud**
- El sistema solo **prioriza pacientes** para atención temprana
