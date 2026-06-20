export function formatDate(isoString) {
  const date = new Date(isoString)
  return date.toLocaleString('es-ES', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

export function parseCSV(content) {
  const lines = content.split('\n')
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
  
  const data = []
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue
    
    // Simple CSV parsing (not handling escaped quotes)
    const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    const row = {}
    headers.forEach((header, index) => {
      row[header] = values[index] || ''
    })
    data.push(row)
  }
  
  return data
}

export function validatePatientData(patients) {
  const errors = []
  
  patients.forEach((patient, index) => {
    if (!patient.nombre || patient.nombre.trim() === '') {
      errors.push(`Fila ${index + 2}: falta el nombre`)
    }
    if (!patient.sintomas || patient.sintomas.trim() === '') {
      errors.push(`Fila ${index + 2}: faltan los síntomas`)
    }
  })
  
  return errors
}
