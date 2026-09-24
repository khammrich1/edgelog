import { describe, expect, it } from 'vitest'
import { computeRealizedR, computeRiskReward, pointsToPrice, priceToPoints } from './tradeMath'

describe('pointsToPrice', () => {
  it('LONG: stop points sit below entry', () => {
    expect(pointsToPrice(20000, 12.5, 'long', 'stop')).toBe(19987.5)
  })

  it('LONG: target points sit above entry', () => {
    expect(pointsToPrice(20000, 25, 'long', 'target')).toBe(20025)
  })

  it('SHORT: stop points sit above entry', () => {
    expect(pointsToPrice(20000, 12.5, 'short', 'stop')).toBe(20012.5)
  })

  it('SHORT: target points sit below entry', () => {
    expect(pointsToPrice(20000, 25, 'short', 'target')).toBe(19975)
  })

  it('returns null when entry price is missing', () => {
    expect(pointsToPrice('', 12.5, 'long', 'stop')).toBeNull()
  })

  it('returns null when points is missing', () => {
    expect(pointsToPrice(20000, '', 'long', 'stop')).toBeNull()
  })
})

describe('priceToPoints', () => {
  it('LONG: stop price below entry converts back to a positive points distance', () => {
    expect(priceToPoints(20000, 19987.5, 'long', 'stop')).toBe(12.5)
  })

  it('LONG: target price above entry converts back to a positive points distance', () => {
    expect(priceToPoints(20000, 20025, 'long', 'target')).toBe(25)
  })

  it('SHORT: stop price above entry converts back to a positive points distance', () => {
    expect(priceToPoints(20000, 20012.5, 'short', 'stop')).toBe(12.5)
  })

  it('SHORT: target price below entry converts back to a positive points distance', () => {
    expect(priceToPoints(20000, 19975, 'short', 'target')).toBe(25)
  })

  it('round-trips with pointsToPrice', () => {
    const price = pointsToPrice(24487.75, 8.25, 'short', 'target')
    expect(priceToPoints(24487.75, price, 'short', 'target')).toBe(8.25)
  })

  it('returns null when price is missing', () => {
    expect(priceToPoints(20000, '', 'long', 'stop')).toBeNull()
  })
})

describe('computeRiskReward', () => {
  it('matches the documented example', () => {
    const result = computeRiskReward({
      quantity: 4,
      entryPrice: 20000,
      stopPrice: 19987.5,
      targetPrice: 20025,
      direction: 'long',
      multiplier: 2
    })
    expect(result).toMatchObject({
      quantity: 4,
      riskPoints: 12.5,
      riskDollars: 100,
      rewardPoints: 25,
      rewardDollars: 200,
      rrRatio: 2,
      multiplierKnown: true
    })
  })

  it('omits reward fields when no target is supplied', () => {
    const result = computeRiskReward({
      quantity: 4,
      entryPrice: 20000,
      stopPrice: 19987.5,
      targetPrice: '',
      direction: 'long',
      multiplier: 2
    })
    expect(result.riskPoints).toBe(12.5)
    expect(result.riskDollars).toBe(100)
    expect(result.rewardPoints).toBeNull()
    expect(result.rewardDollars).toBeNull()
    expect(result.rrRatio).toBeNull()
  })

  it('never invents a dollar value for an unknown instrument', () => {
    const result = computeRiskReward({
      quantity: 2,
      entryPrice: 100,
      stopPrice: 95,
      targetPrice: 110,
      direction: 'long',
      multiplier: null
    })
    expect(result.multiplierKnown).toBe(false)
    expect(result.riskDollars).toBeNull()
    expect(result.rewardDollars).toBeNull()
    // Points are instrument-independent, so those still come through.
    expect(result.riskPoints).toBe(5)
    expect(result.rewardPoints).toBe(10)
    expect(result.rrRatio).toBe(2)
  })

  it('works for SHORT direction (stop above, target below)', () => {
    const result = computeRiskReward({
      quantity: 1,
      entryPrice: 5000,
      stopPrice: 5010,
      targetPrice: 4980,
      direction: 'short',
      multiplier: 5
    })
    expect(result.riskPoints).toBe(10)
    expect(result.riskDollars).toBe(50)
    expect(result.rewardPoints).toBe(20)
    expect(result.rewardDollars).toBe(100)
    expect(result.rrRatio).toBe(2)
  })

  it('returns null with no quantity or no entry price', () => {
    expect(computeRiskReward({ quantity: '', entryPrice: 100, direction: 'long' })).toBeNull()
    expect(computeRiskReward({ quantity: 1, entryPrice: '', direction: 'long' })).toBeNull()
  })
})

describe('computeRealizedR', () => {
  it('computes a positive R-multiple for a winning trade', () => {
    expect(computeRealizedR(200, 100)).toBe(2)
  })

  it('computes a negative R-multiple for a losing trade', () => {
    expect(computeRealizedR(-150, 100)).toBe(-1.5)
  })

  it('uses the absolute value of planned risk as the denominator', () => {
    expect(computeRealizedR(200, -100)).toBe(2)
  })

  it('returns null when realized P&L is missing', () => {
    expect(computeRealizedR(null, 100)).toBeNull()
    expect(computeRealizedR(undefined, 100)).toBeNull()
  })

  it('returns null when planned risk is missing or zero', () => {
    expect(computeRealizedR(200, null)).toBeNull()
    expect(computeRealizedR(200, 0)).toBeNull()
  })
})
