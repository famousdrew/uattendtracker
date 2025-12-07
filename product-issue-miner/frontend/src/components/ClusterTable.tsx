'use client'

import { useState } from 'react'
import { Cluster } from '@/lib/api'
import { format, parseISO } from 'date-fns'
import Link from 'next/link'

interface ClusterTableProps {
  clusters: Cluster[]
  onClusterClick?: (id: string) => void
}

type SortField = 'cluster_name' | 'issue_count' | 'unique_customers' | 'trend_pct' | 'last_seen'
type SortDirection = 'asc' | 'desc'

export default function ClusterTable({ clusters, onClusterClick }: ClusterTableProps) {
  const [sortField, setSortField] = useState<SortField>('issue_count')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const sortedClusters = [...clusters].sort((a, b) => {
    let aVal: any = a[sortField]
    let bVal: any = b[sortField]

    if (sortField === 'last_seen') {
      aVal = new Date(aVal).getTime()
      bVal = new Date(bVal).getTime()
    }

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
    return 0
  })

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      )
    }
    return sortDirection === 'asc' ? (
      <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    )
  }

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      new: { label: 'New', className: 'bg-blue-100 text-blue-800' },
      reviewing: { label: 'Reviewing', className: 'bg-yellow-100 text-yellow-800' },
      acknowledged: { label: 'Acknowledged', className: 'bg-purple-100 text-purple-800' },
      fixed: { label: 'Fixed', className: 'bg-green-100 text-green-800' },
      wont_fix: { label: "Won't Fix", className: 'bg-gray-100 text-gray-800' },
    }
    const config = statusConfig[status] || statusConfig.new
    return <span className={`badge ${config.className}`}>{config.label}</span>
  }

  const getTrendIndicator = (trendPct: number) => {
    if (trendPct > 0) {
      return (
        <span className="inline-flex items-center text-trend-up">
          <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
          +{trendPct.toFixed(0)}%
        </span>
      )
    } else if (trendPct < 0) {
      return (
        <span className="inline-flex items-center text-trend-down">
          <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
          {trendPct.toFixed(0)}%
        </span>
      )
    }
    return <span className="text-trend-neutral">0%</span>
  }

  if (clusters.length === 0) {
    return (
      <div className="dashboard-card text-center py-12">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No clusters found</h3>
        <p className="mt-1 text-sm text-gray-500">Try adjusting your filters</p>
      </div>
    )
  }

  return (
    <div className="dashboard-card overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('cluster_name')}
              >
                <div className="flex items-center space-x-1">
                  <span>Cluster Name</span>
                  <SortIcon field="cluster_name" />
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('issue_count')}
              >
                <div className="flex items-center space-x-1">
                  <span>Issues</span>
                  <SortIcon field="issue_count" />
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('unique_customers')}
              >
                <div className="flex items-center space-x-1">
                  <span>Customers</span>
                  <SortIcon field="unique_customers" />
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('trend_pct')}
              >
                <div className="flex items-center space-x-1">
                  <span>Trend</span>
                  <SortIcon field="trend_pct" />
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('last_seen')}
              >
                <div className="flex items-center space-x-1">
                  <span>Last Seen</span>
                  <SortIcon field="last_seen" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedClusters.map((cluster) => (
              <tr
                key={cluster.id}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => onClusterClick?.(cluster.id)}
              >
                <td className="px-6 py-4">
                  <Link
                    href={`/clusters/${cluster.id}`}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {cluster.cluster_name}
                  </Link>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                    {cluster.cluster_summary}
                  </p>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{cluster.category}</div>
                  <div className="text-sm text-gray-500">{cluster.subcategory}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {cluster.issue_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {cluster.unique_customers}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {getTrendIndicator(cluster.trend_pct)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(cluster.pm_status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {format(parseISO(cluster.last_seen), 'MMM dd, yyyy')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function ClusterTableSkeleton() {
  return (
    <div className="dashboard-card overflow-hidden p-0 animate-pulse">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {['Cluster Name', 'Category', 'Issues', 'Customers', 'Trend', 'Status', 'Last Seen'].map((header) => (
                <th key={header} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {[...Array(5)].map((_, i) => (
              <tr key={i}>
                <td className="px-6 py-4">
                  <div className="h-4 bg-gray-200 rounded w-48 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-64"></div>
                </td>
                <td className="px-6 py-4">
                  <div className="h-4 bg-gray-200 rounded w-24 mb-1"></div>
                  <div className="h-3 bg-gray-200 rounded w-20"></div>
                </td>
                <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-8"></div></td>
                <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-8"></div></td>
                <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12"></div></td>
                <td className="px-6 py-4"><div className="h-6 bg-gray-200 rounded-full w-20"></div></td>
                <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
