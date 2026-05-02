import { describe, it, expect } from 'vitest'
import { parsePrUrl } from '@/api/client'

describe('parsePrUrl', () => {
  it('parses a standard GitHub PR URL', () => {
    const result = parsePrUrl('https://github.com/myorg/myrepo/pull/42')
    expect(result).toMatchObject({
      owner: 'myorg',
      repo: 'myrepo',
      pr_number: 42,
    })
  })

  it('parses a PR URL with trailing slash', () => {
    const result = parsePrUrl('https://github.com/myorg/myrepo/pull/42/')
    expect(result).toMatchObject({
      owner: 'myorg',
      repo: 'myrepo',
      pr_number: 42,
    })
  })

  it('returns null for non-PR URL', () => {
    expect(parsePrUrl('https://github.com/myorg/myrepo')).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(parsePrUrl('')).toBeNull()
  })

  it('returns null for arbitrary string', () => {
    expect(parsePrUrl('not-a-url')).toBeNull()
  })
})
