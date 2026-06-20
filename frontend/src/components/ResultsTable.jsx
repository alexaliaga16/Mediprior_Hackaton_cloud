import './ResultsTable.css'

const URGENCY_CONFIG = {
  CRITICO: { color: '#dc2626', label: '🔴 Crítico', priority: 1 },
  URGENTE: { color: '#f59e0b', label: '🟠 Urgente', priority: 2 },
  MODERADO: { color: '#0284c7', label: '🔵 Moderado', priority: 3 },
  LEVE: { color: '#10b981', label: '🟢 Leve', priority: 4 },
}

export default function ResultsTable({ patients }) {
  // Ordenar por urgencia
  const sortedPatients = [...patients].sort((a, b) => {
    const configA = URGENCY_CONFIG[a.urgencia]?.priority ?? 999
    const configB = URGENCY_CONFIG[b.urgencia]?.priority ?? 999
    return configA - configB
  })

  if (sortedPatients.length === 0) {
    return (
      <div className="empty-state">
        <p>No hay resultados disponibles</p>
      </div>
    )
  }

  return (
    <div className="results-wrapper">
      <div className="results-grid">
        {sortedPatients.map((patient) => (
          <PatientCard key={patient.patientId} patient={patient} />
        ))}
      </div>
    </div>
  )
}

function PatientCard({ patient }) {
  const urgencyConfig = URGENCY_CONFIG[patient.urgencia] || {}
  const riskLevel = patient.riesgo || 0

  return (
    <div className="patient-card">
      <div className="card-header" style={{ borderLeftColor: urgencyConfig.color }}>
        <div className="card-title">
          <h3>{patient.nombre}</h3>
          <span className="urgency-badge" style={{ backgroundColor: urgencyConfig.color }}>
            {urgencyConfig.label}
          </span>
        </div>
        <div className="risk-score">
          <span className="risk-label">Riesgo</span>
          <span className="risk-value" style={{ color: urgencyConfig.color }}>
            {riskLevel}%
          </span>
        </div>
      </div>

      <div className="card-body">
        <div className="section">
          <label>Síntomas reportados</label>
          <p className="symptoms">{patient.sintomas}</p>
        </div>

        <div className="section">
          <label>Especialidad recomendada</label>
          <p className="specialty">{patient.especialidad || 'No especificada'}</p>
        </div>

        {patient.alerta && (
          <div className="section alert-section">
            <label>⚠️ Alerta</label>
            <p className="alert-text">{patient.alerta}</p>
          </div>
        )}

        <div className="section">
          <label>Recomendación</label>
          <p className="recommendation">{patient.recomendacion || 'Evaluación estándar'}</p>
        </div>

        {patient.justificacion && (
          <details className="section">
            <summary>Ver análisis detallado</summary>
            <p className="justification">{patient.justificacion}</p>
          </details>
        )}

        {patient.status && (
          <div className="card-footer">
            <span className="status-badge" data-status={patient.status}>
              {patient.status === 'DONE' ? '✓ Procesado' : '⏳ Procesando'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
