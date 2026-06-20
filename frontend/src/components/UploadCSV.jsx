import { useRef } from 'react'
import './UploadCSV.css'

export default function UploadCSV({ onUpload, loading }) {
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validar que sea CSV
      if (!file.name.endsWith('.csv')) {
        alert('Por favor selecciona un archivo CSV')
        return
      }
      onUpload(file)
      // Reset para permitir subir el mismo archivo nuevamente
      fileInputRef.current.value = ''
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.currentTarget.classList.add('drag-over')
  }

  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('drag-over')
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.currentTarget.classList.remove('drag-over')
    const file = e.dataTransfer.files?.[0]
    if (file && file.name.endsWith('.csv')) {
      onUpload(file)
    } else {
      alert('Por favor arrastra un archivo CSV')
    }
  }

  return (
    <div className="upload-container">
      <div className="upload-box">
        <h2>Sube tu archivo CSV</h2>
        
        <div 
          className="upload-area"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="upload-icon">📄</div>
          <h3>Arrastra tu archivo aquí</h3>
          <p>o haz clic para seleccionar</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            disabled={loading}
            style={{ display: 'none' }}
          />
        </div>

        <button
          className="btn btn-primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
        >
          {loading ? '⏳ Subiendo...' : '📤 Seleccionar archivo'}
        </button>
      </div>

      <div className="upload-info">
        <h3>Formato esperado del CSV</h3>
        <div className="info-box">
          <p><strong>Columnas requeridas:</strong></p>
          <ul>
            <li><code>nombre</code> - Nombre del paciente</li>
            <li><code>sintomas</code> - Descripción de síntomas en texto libre</li>
          </ul>
          <p className="mt-2"><strong>Ejemplo:</strong></p>
          <div className="csv-example">
nombre,sintomas<br/>
Juan Pérez,"el señor llegó con el pecho apretado, sudando frío"<br/>
María García,"dolor intenso de cabeza, visión borrosa"
          </div>
        </div>
      </div>

      <div className="upload-sample">
        <h3>Descargar plantilla de ejemplo</h3>
        <button className="btn btn-secondary" onClick={downloadSample}>
          📥 pacientes_ejemplo.csv
        </button>
      </div>
    </div>
  )
}

function downloadSample() {
  const csv = `nombre,sintomas
Juan Pérez,"el señor llegó con el pecho apretado, sudando frío y con el brazo izquierdo adormecido desde hace 20 minutos"
María García,"dolor intenso de cabeza, acompañado de rigidez en el cuello"
Carlos López,"fiebre alta (39.5°C), tos seca y dificultad para respirar"
Ana Martínez,"dolor abdominal severo, vómitos desde hace 6 horas"
Roberto Sánchez,"caída de altura, dolor en pierna y sangrado activo"
`
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'pacientes_ejemplo.csv'
  a.click()
  window.URL.revokeObjectURL(url)
}
