import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import UploadCSV from './components/UploadCSV'
import ProgressBar from './components/ProgressBar'
import ResultsTable from './components/ResultsTable'
import MetricsDashboard from './components/MetricsDashboard'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://h2fki8xkz7.execute-api.us-east-1.amazonaws.com'
const MAX_POLL_ERRORS = 5

export default function App() {
  const [currentStep, setCurrentStep] = useState('upload')
  const [jobId, setJobId] = useState(null)
  const [jobData, setJobData] = useState(null)
  const [patients, setPatients] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const pollErrorCount = useRef(0)

  useEffect(() => {
    if (currentStep !== 'processing' || !jobId) return

    pollErrorCount.current = 0

    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/results/${jobId}`)
        const { job, patients: patientsData, metrics: metricsData } = response.data

        pollErrorCount.current = 0
        setJobData(job)
        if (patientsData) setPatients(patientsData)
        if (metricsData) setMetrics(metricsData)

        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          clearInterval(pollInterval)
          setCurrentStep('results')
        }
      } catch (err) {
        pollErrorCount.current += 1
        console.error('Error fetching results:', err)
        if (pollErrorCount.current >= MAX_POLL_ERRORS) {
          clearInterval(pollInterval)
          setError(`No se pudo obtener el estado del procesamiento. ${err.response?.data?.message || err.message}`)
          setCurrentStep('upload')
        }
      }
    }, 3000)

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
      setPatients([])
      setMetrics(null)
      setJobData({ status: 'PROCESSING', processedPatients: 0, totalPatients: total })
      setCurrentStep('processing')
    } catch (err) {
      const message = err.response?.data?.message || 'Error al subir el archivo. Verifica la conexión.'
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
    setMetrics(null)
    setError(null)
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
            </div>
            {metrics && <MetricsDashboard metrics={metrics} total={jobData?.totalPatients} />}
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
