import { useState, useEffect } from 'react'
import axios from 'axios'
import UploadCSV from './components/UploadCSV'
import ProgressBar from './components/ProgressBar'
import ResultsTable from './components/ResultsTable'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'

export default function App() {
  const [currentStep, setCurrentStep] = useState('upload') // upload, processing, results
  const [jobId, setJobId] = useState(null)
  const [jobData, setJobData] = useState(null)
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [totalPatients, setTotalPatients] = useState(0)

  // Polling para obtener resultados
  useEffect(() => {
    if (currentStep !== 'processing' || !jobId) return

    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/results/${jobId}`)
        const { job, patients: patientsData } = response.data

        setJobData(job)
        setPatients(patientsData || [])

        // Si completó, cambiar a resultados
        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          setCurrentStep('results')
          clearInterval(pollInterval)
        }
      } catch (err) {
        console.error('Error fetching results:', err)
      }
    }, 2000) // polling cada 2 segundos

    return () => clearInterval(pollInterval)
  }, [currentStep, jobId])

  const handleUpload = async (file) => {
    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const { jobId: newJobId, totalPatients: total } = response.data

      setJobId(newJobId)
      setTotalPatients(total)
      setJobData({ status: 'PROCESSING', processedPatients: 0, totalPatients: total })
      setCurrentStep('processing')
    } catch (err) {
      const message = err.response?.data?.message || 'Error al subir archivo'
      setError(message)
      console.error('Upload error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setCurrentStep('upload')
    setJobId(null)
    setJobData(null)
    setPatients([])
    setError(null)
    setTotalPatients(0)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="container">
          <div className="header-content">
            <div>
              <h1>MediPrior</h1>
              <p className="subtitle">Priorización Clínica Asistida por IA</p>
            </div>
            <div className="header-badge">
              <span className="badge-label">Powered by</span>
              <span className="badge-value">Groq LLM</span>
            </div>
          </div>
        </div>
      </header>

      <main className="container main-content">
        {error && (
          <div className="error-box">
            <span className="error-icon">⚠️</span>
            <div>
              <strong>Error</strong>
              <p>{error}</p>
            </div>
            <button className="btn-close" onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {currentStep === 'upload' && (
          <UploadCSV onUpload={handleUpload} loading={loading} />
        )}

        {currentStep === 'processing' && jobData && (
          <div className="processing-section">
            <h2 className="text-center">Procesando pacientes...</h2>
            <ProgressBar
              current={jobData.processedPatients}
              total={jobData.totalPatients}
            />
            <p className="processing-text">
              {jobData.processedPatients} de {jobData.totalPatients} pacientes procesados
            </p>
          </div>
        )}

        {currentStep === 'results' && (
          <div className="results-section">
            <div className="results-header">
              <h2>Resultados de Priorización</h2>
              {jobData && (
                <div className="results-stats">
                  <span>Total: {jobData.totalPatients}</span>
                  <span>Procesados: {jobData.processedPatients}</span>
                </div>
              )}
            </div>
            {patients.length > 0 ? (
              <ResultsTable patients={patients} />
            ) : (
              <p className="text-center">No hay resultados disponibles</p>
            )}
            <button className="btn btn-primary mt-4" onClick={handleReset}>
              Procesar otro archivo
            </button>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>El sistema prioriza pacientes. La decisión final es siempre del profesional de salud.</p>
      </footer>
    </div>
  )
}
