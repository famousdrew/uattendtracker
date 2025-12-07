// Type definitions for API responses
export interface IssueSummary {
  total_issues: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  trending_up: number
}

export interface TrendDataPoint {
  date: string
  count: number
}

export interface TrendData {
  trends: TrendDataPoint[]
}

export interface Ticket {
  zendesk_ticket_id: number
  subject: string
  requester_org_name: string
  ticket_created_at: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  zendesk_url: string
}

export interface Cluster {
  id: string
  cluster_name: string
  cluster_summary: string
  category: string
  subcategory: string
  issue_count: number
  unique_customers: number
  trend_pct: number
  pm_status: 'new' | 'reviewing' | 'acknowledged' | 'fixed' | 'wont_fix'
  pm_notes: string
  last_seen: string
  is_active: boolean
  created_at: string
}

export interface ClusterList {
  clusters: Cluster[]
  total_count: number
}

export interface ClusterDetail extends Cluster {
  tickets: Ticket[]
}

export interface UpdateClusterRequest {
  pm_status?: 'new' | 'reviewing' | 'acknowledged' | 'fixed' | 'wont_fix'
  pm_notes?: string
}

export interface FilterParams {
  category?: string
  subcategory?: string
  pm_status?: string
  is_active?: boolean
  sort_by?: string
  page?: number
  limit?: number
}

// API Client
export class ApiClient {
  private baseUrl: string
  private password: string | null = null

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  }

  setPassword(password: string) {
    this.password = password
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (this.password) {
      headers['X-Dashboard-Password'] = this.password
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('Authentication failed')
      }
      throw new Error(`API error: ${response.statusText}`)
    }

    return response.json()
  }

  async getIssuesSummary(): Promise<IssueSummary> {
    return this.fetch<IssueSummary>('/api/issues/summary')
  }

  async getIssuesTrends(): Promise<TrendData> {
    return this.fetch<TrendData>('/api/issues/trends')
  }

  async getClusters(params?: FilterParams): Promise<ClusterList> {
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.append('category', params.category)
    if (params?.subcategory) searchParams.append('subcategory', params.subcategory)
    if (params?.pm_status) searchParams.append('pm_status', params.pm_status)
    if (params?.is_active !== undefined) searchParams.append('is_active', params.is_active.toString())
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.limit) searchParams.append('limit', params.limit.toString())

    const query = searchParams.toString()
    const endpoint = query ? `/api/clusters?${query}` : '/api/clusters'
    return this.fetch<ClusterList>(endpoint)
  }

  async getCluster(clusterId: string): Promise<ClusterDetail> {
    return this.fetch<ClusterDetail>(`/api/clusters/${clusterId}`)
  }

  async updateCluster(
    clusterId: string,
    data: UpdateClusterRequest
  ): Promise<ClusterDetail> {
    return this.fetch<ClusterDetail>(`/api/clusters/${clusterId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async getCategories(): Promise<string[]> {
    const result = await this.getClusters()
    const categories = new Set(result.clusters.map(c => c.category))
    return Array.from(categories).sort()
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
