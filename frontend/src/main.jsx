import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './reserva.css'

const raiz = document.getElementById('reserva-root')
createRoot(raiz).render(
  <StrictMode>
    <App loginUrl={raiz.dataset.loginUrl} registroUrl={raiz.dataset.registroUrl} />
  </StrictMode>,
)
