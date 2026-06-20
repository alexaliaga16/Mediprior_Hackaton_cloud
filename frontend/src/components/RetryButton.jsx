import { useState } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://h2fki8xkz7.execute-api.us-east-1.amazonaws.com'

export default function RetryButton({ patients, jobId }) {
  const [retrying, setRetrying] = useState(false)
  const [successMsg, setSuccessMsg] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)

  const failedCount = patients.filter(p => p.status === 'FAILED').length

  if (failedCount === 0) return null

  const handleRetry = async () => {
    setRetrying(true)
    setSuccessMsg(null)
    setErrorMsg(null)

    try {
      await axios.post(`${API_BASE_URL}/retry-failed`, { jobId })
      setSuccessMsg(`${failedCount} paciente${failedCount !== 1 ? 's' : ''} reenviado${failedCount !== 1 ? 's' : ''} para reprocesamiento`)
    } catch (err) {
      setErrorMsg(err.response?.data?.message || 'Error al reintentar. Inténtalo de nuevo.')
    } finally {
      setRetrying(false)
    }
  }

  return (
    <div style={{
      margin: '0 0 1.5rem 0',
      padding: '1rem 1.25rem',
      background: '#fff5f5',
      border: '1px solid #fca5a5',
      borderRadius: '0.75rem',
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      flexWrap: 'wrap',
    }}>
      <span style={{ color: '#7f1d1d', fontWeight: 500, fontSize: '0.95rem' }}>
        {failedCount} paciente{failedCount !== 1 ? 's' : ''} no pudo ser procesado{failedCount !== 1 ? 's' : ''}
      </span>

      {!successMsg && (
        <button
          onClick={handleRetry}
          disabled={retrying}
          style={{
            background: retrying ? '#9ca3af' : '#dc2626',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            padding: '0.5rem 1.1rem',
            fontWeight: 600,
            fontSize: '0.9rem',
            cursor: retrying ? 'not-allowed' : 'pointer',
            transition: 'background 0.2s',
          }}
        >
          {retrying ? '⏳ Reintentando...' : `🔄 Reintentar pacientes fallidos (${failedCount})`}
        </button>
      )}

      {successMsg && (
        <span style={{ color: '#166534', fontWeight: 500, fontSize: '0.9rem' }}>
          ✓ {successMsg}
        </span>
      )}

      {errorMsg && (
        <span style={{ color: '#dc2626', fontSize: '0.9rem' }}>
          ⚠️ {errorMsg}
        </span>
      )}
    </div>
  )
}
