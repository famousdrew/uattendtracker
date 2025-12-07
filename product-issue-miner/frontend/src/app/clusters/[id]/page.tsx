'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import StatusEditor from '@/components/StatusEditor'
import TicketTable, { TicketTableSkeleton } from '@/components/TicketTable'
import { format, parseISO } from 'date-fns'

export default function ClusterDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const queryClient = useQueryClient()

  // Fetch cluster details
  const { data: cluster, isLoading, error } = useQuery({
    queryKey: ['clusters', params.id],
    queryFn: () => apiClient.getCluster(params.id),
  })

  // Mutation for updating cluster status
  const updateMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes: string }) =>
      apiClient.updateCluster(params.id, { pm_status: status as any, pm_notes: notes }),
    onSuccess: (updatedCluster) => {
      // Update cache
      queryClient.setQueryData(['clusters', params.id], updatedCluster)
      // Invalidate cluster list queries
      queryClient.invalidateQueries({ queryKey: ['clusters', 'list'] })
      queryClient.invalidateQueries({ queryKey: ['clusters', 'top'] })
    },
  })

  const handleSave = async (status: string, notes: string) => {
    await updateMutation.mutateAsync({ status, notes })
  }

  const handleBack = () => {
    router.back()
  }

  const getTrendIndicator = (trendPct: number) => {
    if (trendPct > 0) {
      return (
        <span className="inline-flex items-center text-trend-up">
          <svg className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
          +{trendPct.toFixed(0)}%
        </span>
      )
    } else if (trendPct < 0) {
      return (
        <span className="inline-flex items-center text-trend-down">
          <svg className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
          {trendPct.toFixed(0)}%
        </span>
      )
    }
    return <span className="text-trend-neutral">0%</span>
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-64 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-96"></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="dashboard-card animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
              <div className="h-6 bg-gray-200 rounded w-16"></div>
            </div>
          ))}
        </div>

        <div className="dashboard-card animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        </div>

        <TicketTableSkeleton />
      </div>
    )
  }

  // Error state
  if (error || !cluster) {
    return (
      <div className="space-y-8">
        <button onClick={handleBack} className="btn-secondary">
          Back to Clusters
        </button>

        <div className="dashboard-card text-center py-12">
          <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Error Loading Cluster</h3>
          <p className="mt-1 text-sm text-gray-500">
            {error instanceof Error ? error.message : 'Cluster not found'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Back Button */}
      <button onClick={handleBack} className="btn-secondary inline-flex items-center">
        <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Clusters
      </button>

      {/* Cluster Header */}
      <div>
        <h1 className="dashboard-header">{cluster.cluster_name}</h1>
        <p className="text-gray-600 mt-2">{cluster.cluster_summary}</p>
        <div className="flex items-center space-x-4 mt-4 text-sm text-gray-500">
          <span className="inline-flex items-center">
            <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
            {cluster.category} / {cluster.subcategory}
          </span>
          <span className="inline-flex items-center">
            <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Last seen: {format(parseISO(cluster.last_seen), 'MMMM dd, yyyy')}
          </span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="dashboard-card">
          <p className="text-sm text-gray-600 mb-1">Total Issues</p>
          <p className="text-3xl font-bold text-gray-900">{cluster.issue_count}</p>
        </div>
        <div className="dashboard-card">
          <p className="text-sm text-gray-600 mb-1">Unique Customers</p>
          <p className="text-3xl font-bold text-gray-900">{cluster.unique_customers}</p>
        </div>
        <div className="dashboard-card">
          <p className="text-sm text-gray-600 mb-1">Trend</p>
          <p className="text-2xl font-bold">{getTrendIndicator(cluster.trend_pct)}</p>
        </div>
        <div className="dashboard-card">
          <p className="text-sm text-gray-600 mb-1">Status</p>
          <span className={`badge ${
            cluster.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {cluster.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      {/* Status Editor */}
      <StatusEditor
        clusterId={cluster.id}
        currentStatus={cluster.pm_status}
        currentNotes={cluster.pm_notes}
        onSave={handleSave}
      />

      {/* Associated Tickets */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title mb-0">Associated Tickets</h2>
          <span className="text-sm text-gray-500">
            {cluster.tickets.length} ticket{cluster.tickets.length !== 1 ? 's' : ''}
          </span>
        </div>
        <TicketTable tickets={cluster.tickets} />
      </div>
    </div>
  )
}
