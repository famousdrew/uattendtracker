'use client'

import { useState, useEffect } from 'react'

export interface FilterState {
  category?: string
  subcategory?: string
  pm_status?: string
  is_active?: boolean
  sort_by?: string
}

interface FiltersProps {
  categories: string[]
  subcategories: string[]
  onFilterChange: (filters: FilterState) => void
  initialFilters?: FilterState
}

export default function Filters({
  categories,
  subcategories,
  onFilterChange,
  initialFilters = {},
}: FiltersProps) {
  const [filters, setFilters] = useState<FilterState>(initialFilters)
  const [availableSubcategories, setAvailableSubcategories] = useState<string[]>(subcategories)

  useEffect(() => {
    // Filter subcategories based on selected category
    if (filters.category && filters.category !== 'all') {
      // In a real implementation, you'd filter based on the actual relationship
      setAvailableSubcategories(subcategories)
    } else {
      setAvailableSubcategories(subcategories)
    }
  }, [filters.category, subcategories])

  const handleFilterChange = (key: keyof FilterState, value: any) => {
    const newFilters = { ...filters }

    if (value === 'all' || value === '') {
      delete newFilters[key]
    } else {
      newFilters[key] = value
    }

    // Reset subcategory if category changes
    if (key === 'category' && filters.subcategory) {
      delete newFilters.subcategory
    }

    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const handleReset = () => {
    setFilters({})
    onFilterChange({})
  }

  const hasActiveFilters = Object.keys(filters).length > 0

  return (
    <div className="dashboard-card">
      <div className="flex flex-col lg:flex-row lg:items-end gap-4">
        {/* Category Filter */}
        <div className="flex-1">
          <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
            Category
          </label>
          <select
            id="category"
            value={filters.category || 'all'}
            onChange={(e) => handleFilterChange('category', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        {/* Subcategory Filter */}
        <div className="flex-1">
          <label htmlFor="subcategory" className="block text-sm font-medium text-gray-700 mb-2">
            Subcategory
          </label>
          <select
            id="subcategory"
            value={filters.subcategory || 'all'}
            onChange={(e) => handleFilterChange('subcategory', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={!filters.category && availableSubcategories.length === 0}
          >
            <option value="all">All Subcategories</option>
            {availableSubcategories.map((subcat) => (
              <option key={subcat} value={subcat}>
                {subcat}
              </option>
            ))}
          </select>
        </div>

        {/* PM Status Filter */}
        <div className="flex-1">
          <label htmlFor="pm_status" className="block text-sm font-medium text-gray-700 mb-2">
            PM Status
          </label>
          <select
            id="pm_status"
            value={filters.pm_status || 'all'}
            onChange={(e) => handleFilterChange('pm_status', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="reviewing">Reviewing</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="fixed">Fixed</option>
            <option value="wont_fix">Won't Fix</option>
          </select>
        </div>

        {/* Active/Inactive Toggle */}
        <div className="flex-1">
          <label htmlFor="is_active" className="block text-sm font-medium text-gray-700 mb-2">
            Status
          </label>
          <select
            id="is_active"
            value={filters.is_active === undefined ? 'all' : filters.is_active.toString()}
            onChange={(e) => {
              const value = e.target.value
              handleFilterChange('is_active', value === 'all' ? undefined : value === 'true')
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>

        {/* Sort By */}
        <div className="flex-1">
          <label htmlFor="sort_by" className="block text-sm font-medium text-gray-700 mb-2">
            Sort By
          </label>
          <select
            id="sort_by"
            value={filters.sort_by || 'issue_count'}
            onChange={(e) => handleFilterChange('sort_by', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="issue_count">Issue Count</option>
            <option value="unique_customers">Customer Count</option>
            <option value="trend_pct">Trend</option>
            <option value="last_seen">Last Seen</option>
            <option value="created_at">Created Date</option>
          </select>
        </div>

        {/* Reset Button */}
        {hasActiveFilters && (
          <div className="flex-shrink-0">
            <button
              onClick={handleReset}
              className="btn-secondary w-full lg:w-auto"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-gray-500">Active filters:</span>
          {filters.category && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
              Category: {filters.category}
              <button
                onClick={() => handleFilterChange('category', 'all')}
                className="ml-2 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          )}
          {filters.subcategory && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
              Subcategory: {filters.subcategory}
              <button
                onClick={() => handleFilterChange('subcategory', 'all')}
                className="ml-2 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          )}
          {filters.pm_status && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
              Status: {filters.pm_status}
              <button
                onClick={() => handleFilterChange('pm_status', 'all')}
                className="ml-2 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          )}
          {filters.is_active !== undefined && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
              {filters.is_active ? 'Active' : 'Inactive'}
              <button
                onClick={() => handleFilterChange('is_active', 'all')}
                className="ml-2 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  )
}
