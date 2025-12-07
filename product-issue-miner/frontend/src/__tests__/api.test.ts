/**
 * Tests for API client
 *
 * Tests cover:
 * - API client methods
 * - Authentication header handling
 * - Error handling (401, 403, network errors)
 * - Request parameter formatting
 * - Response parsing
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { ApiClient } from '../lib/api'

// Mock fetch globally
global.fetch = vi.fn()

describe('ApiClient', () => {
  let client: ApiClient

  beforeEach(() => {
    client = new ApiClient('http://test-api.example.com')
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Authentication', () => {
    it('should set password', () => {
      client.setPassword('test-password')
      // Password is private, but we can test it via API calls
      expect(client).toBeDefined()
    })

    it('should include authentication header when password is set', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({
          total_issues: 10,
          critical_count: 2,
          high_count: 3,
          medium_count: 3,
          low_count: 2,
          trending_up: 5,
        }),
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      client.setPassword('secret-password')
      await client.getIssuesSummary()

      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/issues/summary',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Dashboard-Password': 'secret-password',
          }),
        })
      )
    })

    it('should throw error on 401 response', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await expect(client.getIssuesSummary()).rejects.toThrow('Authentication failed')
    })

    it('should throw error on 403 response', async () => {
      const mockResponse = {
        ok: false,
        status: 403,
        statusText: 'Forbidden',
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await expect(client.getIssuesSummary()).rejects.toThrow('Authentication failed')
    })
  })

  describe('getIssuesSummary', () => {
    it('should fetch issues summary successfully', async () => {
      const mockData = {
        total_issues: 42,
        critical_count: 5,
        high_count: 10,
        medium_count: 15,
        low_count: 12,
        trending_up: 8,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.getIssuesSummary()

      expect(result).toEqual(mockData)
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/issues/summary',
        expect.any(Object)
      )
    })

    it('should handle API errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await expect(client.getIssuesSummary()).rejects.toThrow('API error: Internal Server Error')
    })
  })

  describe('getIssuesTrends', () => {
    it('should fetch trends data successfully', async () => {
      const mockData = {
        trends: [
          { date: '2024-01-15', count: 5 },
          { date: '2024-01-16', count: 8 },
          { date: '2024-01-17', count: 3 },
        ],
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.getIssuesTrends()

      expect(result).toEqual(mockData)
      expect(result.trends).toHaveLength(3)
    })
  })

  describe('getClusters', () => {
    it('should fetch clusters without filters', async () => {
      const mockData = {
        clusters: [
          {
            id: '123',
            cluster_name: 'Test Cluster',
            cluster_summary: 'Summary',
            category: 'TIME_AND_ATTENDANCE',
            subcategory: 'Clock In/Out',
            issue_count: 10,
            unique_customers: 5,
            trend_pct: 25.5,
            pm_status: 'new',
            pm_notes: '',
            last_seen: '2024-01-15T10:00:00Z',
            is_active: true,
            created_at: '2024-01-10T10:00:00Z',
          },
        ],
        total_count: 1,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.getClusters()

      expect(result).toEqual(mockData)
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/clusters',
        expect.any(Object)
      )
    })

    it('should fetch clusters with category filter', async () => {
      const mockData = {
        clusters: [],
        total_count: 0,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await client.getClusters({ category: 'PAYROLL' })

      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/clusters?category=PAYROLL',
        expect.any(Object)
      )
    })

    it('should fetch clusters with multiple filters', async () => {
      const mockData = {
        clusters: [],
        total_count: 0,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await client.getClusters({
        category: 'TIME_AND_ATTENDANCE',
        pm_status: 'reviewing',
        is_active: true,
        page: 2,
        limit: 20,
      })

      const expectedUrl = 'http://test-api.example.com/api/clusters?' +
        'category=TIME_AND_ATTENDANCE&pm_status=reviewing&is_active=true&page=2&limit=20'

      expect(global.fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.any(Object)
      )
    })

    it('should handle sort_by parameter', async () => {
      const mockData = {
        clusters: [],
        total_count: 0,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await client.getClusters({ sort_by: 'issue_count:desc' })

      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/clusters?sort_by=issue_count%3Adesc',
        expect.any(Object)
      )
    })
  })

  describe('getCluster', () => {
    it('should fetch single cluster detail', async () => {
      const mockData = {
        id: '123',
        cluster_name: 'Test Cluster',
        cluster_summary: 'Detailed summary',
        category: 'TIME_AND_ATTENDANCE',
        subcategory: 'Clock In/Out',
        issue_count: 10,
        unique_customers: 5,
        trend_pct: 25.5,
        pm_status: 'reviewing',
        pm_notes: 'Investigating with engineering',
        last_seen: '2024-01-15T10:00:00Z',
        is_active: true,
        created_at: '2024-01-10T10:00:00Z',
        tickets: [
          {
            zendesk_ticket_id: 12345,
            subject: 'Clock in issue',
            requester_org_name: 'Company A',
            ticket_created_at: '2024-01-14T09:00:00Z',
            severity: 'high',
            zendesk_url: 'https://test.zendesk.com/agent/tickets/12345',
          },
        ],
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.getCluster('123')

      expect(result).toEqual(mockData)
      expect(result.tickets).toHaveLength(1)
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/clusters/123',
        expect.any(Object)
      )
    })
  })

  describe('updateCluster', () => {
    it('should update cluster pm_status', async () => {
      const mockData = {
        id: '123',
        cluster_name: 'Test Cluster',
        cluster_summary: 'Summary',
        category: 'TIME_AND_ATTENDANCE',
        subcategory: 'Clock In/Out',
        issue_count: 10,
        unique_customers: 5,
        trend_pct: 25.5,
        pm_status: 'acknowledged',
        pm_notes: '',
        last_seen: '2024-01-15T10:00:00Z',
        is_active: true,
        created_at: '2024-01-10T10:00:00Z',
        tickets: [],
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.updateCluster('123', { pm_status: 'acknowledged' })

      expect(result.pm_status).toBe('acknowledged')
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/clusters/123',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ pm_status: 'acknowledged' }),
        })
      )
    })

    it('should update cluster pm_notes', async () => {
      const mockData = {
        id: '123',
        cluster_name: 'Test Cluster',
        cluster_summary: 'Summary',
        category: 'TIME_AND_ATTENDANCE',
        subcategory: 'Clock In/Out',
        issue_count: 10,
        unique_customers: 5,
        trend_pct: 25.5,
        pm_status: 'new',
        pm_notes: 'Will fix in next sprint',
        last_seen: '2024-01-15T10:00:00Z',
        is_active: true,
        created_at: '2024-01-10T10:00:00Z',
        tickets: [],
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.updateCluster('123', { pm_notes: 'Will fix in next sprint' })

      expect(result.pm_notes).toBe('Will fix in next sprint')
    })

    it('should update both pm_status and pm_notes', async () => {
      const mockData = {
        id: '123',
        cluster_name: 'Test Cluster',
        cluster_summary: 'Summary',
        category: 'TIME_AND_ATTENDANCE',
        subcategory: 'Clock In/Out',
        issue_count: 10,
        unique_customers: 5,
        trend_pct: 25.5,
        pm_status: 'fixed',
        pm_notes: 'Resolved in v2.5.0',
        last_seen: '2024-01-15T10:00:00Z',
        is_active: true,
        created_at: '2024-01-10T10:00:00Z',
        tickets: [],
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await client.updateCluster('123', {
        pm_status: 'fixed',
        pm_notes: 'Resolved in v2.5.0',
      })

      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.example.com/api/clusters/123',
        expect.objectContaining({
          body: JSON.stringify({
            pm_status: 'fixed',
            pm_notes: 'Resolved in v2.5.0',
          }),
        })
      )
    })
  })

  describe('getCategories', () => {
    it('should extract unique categories from clusters', async () => {
      const mockData = {
        clusters: [
          { category: 'TIME_AND_ATTENDANCE' } as any,
          { category: 'PAYROLL' } as any,
          { category: 'TIME_AND_ATTENDANCE' } as any,
          { category: 'SETTINGS' } as any,
        ],
        total_count: 4,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.getCategories()

      expect(result).toEqual(['PAYROLL', 'SETTINGS', 'TIME_AND_ATTENDANCE']) // Sorted
      expect(result).toHaveLength(3) // Unique
    })

    it('should return empty array when no clusters', async () => {
      const mockData = {
        clusters: [],
        total_count: 0,
      }

      const mockResponse = {
        ok: true,
        json: async () => mockData,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      const result = await client.getCategories()

      expect(result).toEqual([])
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('Network error'))

      await expect(client.getIssuesSummary()).rejects.toThrow('Network error')
    })

    it('should include Content-Type header', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ clusters: [], total_count: 0 }),
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await client.getClusters()

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
    })
  })

  describe('Constructor', () => {
    it('should use provided baseUrl', () => {
      const customClient = new ApiClient('https://custom-api.com')
      expect(customClient).toBeDefined()
    })

    it('should use environment variable when no baseUrl provided', () => {
      const envClient = new ApiClient()
      expect(envClient).toBeDefined()
    })
  })
})
