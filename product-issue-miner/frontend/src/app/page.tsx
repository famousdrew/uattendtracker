'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import SummaryCards, { SummaryCardsSkeleton } from '@/components/SummaryCards'
import TrendChart, { TrendChartSkeleton } from '@/components/TrendChart'
import ClusterTable, { ClusterTableSkeleton } from '@/components/ClusterTable'
import { useRouter } from 'next/navigation'
import { subDays, parseISO } from 'date-fns'

export default function Dashboard() {
  const router = useRouter()

  // Fetch summary stats
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['issues', 'summary'],
    queryFn: () => apiClient.getIssuesSummary(),
  })

  // Fetch trend data
  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['issues', 'trends'],
    queryFn: () => apiClient.getIssuesTrends(),
  })

  // Fetch top clusters
  const { data: clustersData, isLoading: clustersLoading } = useQuery({
    queryKey: ['clusters', 'top'],
    queryFn: () => apiClient.getClusters({ sort_by: 'issue_count', limit: 10 }),
  })

  // Fetch emerging issues (new clusters from past 7 days)
  const { data: emergingData, isLoading: emergingLoading } = useQuery({
    queryKey: ['clusters', 'emerging'],
    queryFn: async () => {
      const result = await apiClient.getClusters({ sort_by: 'created_at' })
      // Filter clusters created in the last 7 days
      const sevenDaysAgo = subDays(new Date(), 7)
      return {
        ...result,
        clusters: result.clusters.filter(c =>
          parseISO(c.created_at) >= sevenDaysAgo
        ).slice(0, 5)
      }
    },
  })

  // Handle authentication errors
  if (summaryError) {
    if (summaryError.message === 'Authentication failed') {
      return (
        <div className="dashboard-card text-center py-12">
          <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Authentication Failed</h3>
          <p className="mt-1 text-sm text-gray-500">Invalid password. Please refresh the page to try again.</p>
        </div>
      )
    }

    return (
      <div className="dashboard-card text-center py-12">
        <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error Loading Data</h3>
        <p className="mt-1 text-sm text-gray-500">{summaryError.message}</p>
      </div>
    )
  }

  const handleClusterClick = (id: string) => {
    router.push(`/clusters/${id}`)
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="dashboard-header">Dashboard</h1>
        <p className="text-gray-600">
          Overview of product issues and trends from the past 7 days
        </p>
      </div>

      {/* Summary Cards */}
      {summaryLoading ? (
        <SummaryCardsSkeleton />
      ) : summary ? (
        <SummaryCards
          totalIssues={summary.total_issues}
          criticalCount={summary.critical_count}
          highCount={summary.high_count}
          trendingUp={summary.trending_up}
        />
      ) : null}

      {/* Trend Chart */}
      {trendLoading ? (
        <TrendChartSkeleton />
      ) : trendData ? (
        <TrendChart data={trendData.trends} />
      ) : null}

      {/* Top Clusters */}
      <div>
        <h2 className="section-title">Top Clusters by Issue Count</h2>
        {clustersLoading ? (
          <ClusterTableSkeleton />
        ) : clustersData ? (
          <ClusterTable
            clusters={clustersData.clusters}
            onClusterClick={handleClusterClick}
          />
        ) : null}
      </div>

      {/* Emerging Issues */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title mb-0">Emerging Issues (Past 7 Days)</h2>
          {emergingData && emergingData.clusters.length > 0 && (
            <span className="text-sm text-gray-500">
              {emergingData.clusters.length} new cluster{emergingData.clusters.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {emergingLoading ? (
          <ClusterTableSkeleton />
        ) : emergingData && emergingData.clusters.length > 0 ? (
          <ClusterTable
            clusters={emergingData.clusters}
            onClusterClick={handleClusterClick}
          />
        ) : (
          <div className="dashboard-card text-center py-8">
            <svg className="mx-auto h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-2 text-sm text-gray-500">No new clusters in the past 7 days</p>
          </div>
        )}
      </div>
    </div>
  )
}
