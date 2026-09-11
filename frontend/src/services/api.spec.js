import { describe, expect, it } from 'vitest'
import api from './api'

describe('api client', () => {
  it('uses a relative baseURL so requests inherit the page origin/scheme', () => {
    // A relative baseURL (no scheme/host) is what lets the browser resolve
    // requests against whatever origin served the page. A hard-coded
    // absolute URL (especially with the wrong scheme, e.g. http:// on an
    // https:// deployment) turns a same-origin request into a cross-origin
    // one and the browser blocks it with a CORS error.
    expect(api.defaults.baseURL).toBe('/api/v1')
    expect(api.defaults.baseURL).not.toMatch(/^https?:\/\//)
  })

  it('sends credentials so the HttpOnly refresh cookie is included', () => {
    expect(api.defaults.withCredentials).toBe(true)
  })
})
