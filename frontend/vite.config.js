import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// La app se compila dentro de los estáticos de Django (static/reserva/) con nombres fijos,
// y la plantilla templates/citas/reservar.html la carga con {% static %}.
// En desarrollo, `npm run dev` sirve la app y redirige /api a Django (puerto 8000).
export default defineConfig({
  plugins: [react()],
  base: '/static/reserva/',
  build: {
    outDir: '../static/reserva',
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: 'src/main.jsx',
      output: {
        entryFileNames: 'reserva.js',
        assetFileNames: 'reserva.[ext]',
      },
    },
  },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: { environment: 'node' },
})
