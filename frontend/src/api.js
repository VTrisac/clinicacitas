// Cliente de la API de Django. Usa la sesión del navegador; los POST llevan el token CSRF
// que Django deja en la cookie `csrftoken` al cargar /reservar/.

function csrfToken() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

async function peticion(url, opciones = {}) {
  const resp = await fetch(url, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
    ...opciones,
  })
  const datos = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const mensaje = datos.detail || Object.values(datos).flat()[0] || 'Ha ocurrido un error. Inténtalo de nuevo.'
    throw new Error(mensaje)
  }
  return datos
}

export const api = {
  yo: () => peticion('/api/yo/'),
  servicios: () => peticion('/api/servicios/'),
  profesionales: (servicio) => peticion(`/api/profesionales/?servicio=${servicio}`),
  huecos: (profesional, servicio, desde, dias = 7) =>
    peticion(`/api/huecos/?profesional=${profesional}&servicio=${servicio}&desde=${desde}&dias=${dias}`),
  misCitas: () => peticion('/api/citas/'),
  reservar: (datos) => peticion('/api/citas/', { method: 'POST', body: JSON.stringify(datos) }),
  cancelar: (id) => peticion(`/api/citas/${id}/cancelar/`, { method: 'POST' }),
}
