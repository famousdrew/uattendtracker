'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRouter, useSearchParams } from 'next/navigation'
import { apiClient, FilterParams } from '@/lib/api'
import Filters, { FilterState } from '@/components/Filters'
import ClusterTable, { ClusterTableSkeleton } from '@/components/ClusterTable'

export default function ClustersPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Initialize filters from URL
  const [filters, setFilters] = useState<FilterState>(() => {
    const category = searchParams.get('category') || undefined
    const subcategory = searchParams.get('subcategory') || undefined
    const pm_status = searchParams.get('pm_status') || undefined
    const is_active = searchParams.get('is_active')
    const sort_by = searchParams.get('sort_by') || 'issue_count'

    return {
      category,
      subcategory,
      pm_status,
      is_active: is_active ? is_active === 'true' : undefined,
      sort_by,
    }
  })

  // Fetch all clusters with current filters
  const { data: clustersData, isLoading, error } = useQuery({
    queryKey: ['clusters', 'list', filters],
    queryFn: () => apiClient.getClusters(filters as FilterParams),
  })

  // Fetch categories for filter dropdown
  const { data: categoriesData } = useQuery({
    queryKey: ['clusters', 'categories'],
    queryFn: async () => {
      const result = await apiClient.getClusters()
      const categories = new Set(result.clusters.map(c => c.category))
      const subcategories = new Set(result.clusters.map(c => c.subcategory))
      return {
        categories: Array.from(categories).sort(),
        subcategories: Array.from(subcategories).sort(),
      }
    },
  })

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams()

    if (filters.category) params.set('category', filters.category)
    if (filters.subcategory) params.set('subcategory', filters.subcategory)
    if (filters.pm_status) params.set('pm_status', filters.pm_status)
    if (filters.is_active !== undefined) params.set('is_active', filters.is_active.toString())
    if (filters.sort_by) params.set('sort_by', filters.sort_by)

    const queryString = params.toString()
    const newUrl = queryString ? `/clusters?${queryString}` : '/clusters'

    router.replace(newUrl, { scroll: false })
  }, [filters, router])

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters)
  }

  const handleClusterClick = (id: string) => {
    router.push(`/clusters/${id}`)
  }

  // Handle errors
  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="dashboard-header">All Clusters</h1>
          <p className="text-gray-600">Browse and filter all product issue clusters</p>
        </div>

        <div className="dashboard-card text-center py-12">
          <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Error Loading Data</h3>
          <p className="mt-1 text-sm text-gray-500">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="dashboard-header">All Clusters</h1>
          <p className="text-gray-600">Browse and filter all product issue clusters</p>
        </div>
        {clustersData && (
          <div className="text-right">
            <p className="text-sm text-gray-500">
              Showing {clustersData.clusters.length} of {clustersData.total_count} clusters
            </p>
          </div>
        )}
      </div>

      {/* Filters */}
      {categoriesData && (
        <Filters
          categories={categoriesData.categories}
          subcategories={categoriesData.subcategories}
          onFilterChange={handleFilterChange}
          initialFilters={filters}
        />
      )}

      {/* Clusters Table */}
      {isLoading ? (
        <ClusterTableSkeleton />
      ) : clustersData ? (
        <>
          <ClusterTable
            clusters={clustersData.clusters}
            onClusterClick={handleClusterClick}
          />

          {/* Results summary */}
          {clustersData.clusters.length === 0 && (
            <div className="dashboard-card text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No clusters found</h3>
              <p className="mt-1 text-sm text-gray-500">Try adjusting your filters</p>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
