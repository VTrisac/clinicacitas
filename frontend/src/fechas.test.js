import { describe, expect, it } from 'vitest'
import { aISO, desdeISO, hora, lunesDe, sumarDias } from './fechas.js'

describe('fechas', () => {
  it('ida y vuelta a ISO', () => {
    expect(aISO(desdeISO('2026-11-02'))).toBe('2026-11-02')
  })
  it('lunes de la semana', () => {
    expect(aISO(lunesDe(desdeISO('2026-11-05')))).toBe('2026-11-02') // jueves -> lunes
    expect(aISO(lunesDe(desdeISO('2026-11-08')))).toBe('2026-11-02') // domingo -> lunes anterior
    expect(aISO(lunesDe(desdeISO('2026-11-02')))).toBe('2026-11-02')
  })
  it('sumar días cambia de mes', () => {
    expect(aISO(sumarDias(desdeISO('2026-10-30'), 3))).toBe('2026-11-02')
  })
  it('hora de un ISO con zona', () => {
    expect(hora('2026-11-02T09:15:00+01:00')).toBe('09:15')
  })
})
