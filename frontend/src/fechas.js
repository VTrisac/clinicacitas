// Utilidades de fechas sin librerías. Las fechas "YYYY-MM-DD" se tratan como días locales.

export function aISO(fecha) {
  const y = fecha.getFullYear()
  const m = String(fecha.getMonth() + 1).padStart(2, '0')
  const d = String(fecha.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function desdeISO(texto) {
  const [y, m, d] = texto.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** Lunes de la semana de `fecha`. */
export function lunesDe(fecha) {
  const f = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate())
  const dia = (f.getDay() + 6) % 7 // 0 = lunes
  f.setDate(f.getDate() - dia)
  return f
}

export function sumarDias(fecha, dias) {
  const f = new Date(fecha)
  f.setDate(f.getDate() + dias)
  return f
}

const fmtDia = new Intl.DateTimeFormat('es-ES', { weekday: 'short', day: 'numeric', month: 'short' })
const fmtLargo = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

export const formatoDia = (iso) => fmtDia.format(desdeISO(iso))
export const formatoLargo = (fechaHora) => fmtLargo.format(new Date(fechaHora))
// La hora tal como viene de la API ("2026-11-02T09:15:00+01:00"), sin depender de la zona del navegador
export const hora = (fechaHora) => fechaHora.slice(11, 16)
