import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useInstrumentsStore } from './instruments'

function mountWithMultipliers(multipliers) {
  setActivePinia(createPinia())
  const store = useInstrumentsStore()
  store.multipliers = multipliers
  return store
}

describe('instruments store getMultiplier', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('resolves a bare root symbol', () => {
    const store = mountWithMultipliers({ MNQ: 2, ES: 50 })
    expect(store.getMultiplier('MNQ')).toBe(2)
    expect(store.getMultiplier(' mnq ')).toBe(2)
  })

  it('resolves a dated futures contract (root + month code + year) to its root', () => {
    const store = mountWithMultipliers({ MNQ: 2, NQ: 20, ES: 50, MCL: 100, MGC: 10 })
    expect(store.getMultiplier('MNQZ26')).toBe(2)
    expect(store.getMultiplier('mnqz26')).toBe(2)
    expect(store.getMultiplier('NQZ26')).toBe(20)
    expect(store.getMultiplier('ESH25')).toBe(50)
    expect(store.getMultiplier('MCLZ2026')).toBe(100)
    expect(store.getMultiplier('MGCG6')).toBe(10)
  })

  it('returns null for an unknown symbol and an unknown dated contract', () => {
    const store = mountWithMultipliers({ MNQ: 2 })
    expect(store.getMultiplier('XYZ')).toBeNull()
    expect(store.getMultiplier('XYZZ26')).toBeNull()
  })

  it('returns null for empty/missing input', () => {
    const store = mountWithMultipliers({ MNQ: 2 })
    expect(store.getMultiplier('')).toBeNull()
    expect(store.getMultiplier(null)).toBeNull()
    expect(store.getMultiplier(undefined)).toBeNull()
  })
})
