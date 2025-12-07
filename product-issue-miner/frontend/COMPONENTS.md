# Frontend Dashboard Components

This document provides an overview of the Product Issue Miner dashboard components.

## Components Overview

### 1. SummaryCards.tsx
**Location:** `src/components/SummaryCards.tsx`

Displays four summary cards showing key metrics:
- Total Issues (7 days)
- Critical Issues count
- High Priority count
- Trending Up clusters

**Props:**
```typescript
interface SummaryCardsProps {
  totalIssues: number
  criticalCount: number
  highCount: number
  trendingUp: number
}
```

**Features:**
- Responsive grid layout (1 column mobile, 2 tablet, 4 desktop)
- Color-coded icons for each metric
- Loading skeleton state included
- Uses Tailwind custom severity colors

### 2. TrendChart.tsx
**Location:** `src/components/TrendChart.tsx`

Displays an area chart showing issue trends over 7 days using Recharts.

**Props:**
```typescript
interface TrendChartProps {
  data: { date: string; count: number }[]
}
```

**Features:**
- Responsive chart container
- Gradient fill area chart
- Date formatting with date-fns
- Tooltip with formatted dates
- Loading skeleton state included

### 3. ClusterTable.tsx
**Location:** `src/components/ClusterTable.tsx`

Sortable table displaying cluster information with inline sorting.

**Props:**
```typescript
interface ClusterTableProps {
  clusters: Cluster[]
  onClusterClick?: (id: string) => void
}
```

**Features:**
- Client-side sorting by any column
- Sortable columns: Name, Issues, Customers, Trend, Last Seen
- Trend indicators with arrows (up/down)
- Status badges with color coding
- Click-to-navigate to cluster detail
- Empty state with helpful message
- Loading skeleton state included

### 4. TicketTable.tsx
**Location:** `src/components/TicketTable.tsx`

Displays tickets associated with a cluster.

**Props:**
```typescript
interface TicketTableProps {
  tickets: Ticket[]
}
```

**Features:**
- Severity badges (critical, high, medium, low)
- External links to Zendesk tickets
- Date formatting
- Responsive table layout
- Empty state for no tickets
- Loading skeleton state included

### 5. Filters.tsx
**Location:** `src/components/Filters.tsx`

Advanced filtering controls for cluster list.

**Props:**
```typescript
interface FiltersProps {
  categories: string[]
  subcategories: string[]
  onFilterChange: (filters: FilterState) => void
  initialFilters?: FilterState
}
```

**Features:**
- Category and subcategory dropdowns
- PM Status filter
- Active/Inactive toggle
- Sort by options
- Active filter tags with remove buttons
- Reset filters button
- Responsive layout

### 6. StatusEditor.tsx
**Location:** `src/components/StatusEditor.tsx`

Edit PM status and notes for a cluster.

**Props:**
```typescript
interface StatusEditorProps {
  clusterId: string
  currentStatus: string
  currentNotes: string
  onSave: (status: string, notes: string) => Promise<void>
}
```

**Features:**
- Edit/View mode toggle
- Status dropdown (new, reviewing, acknowledged, fixed, wont_fix)
- Notes textarea
- Save/Cancel buttons
- Loading state during save
- Success/Error messages
- Prevents saving without changes

### 7. Navigation.tsx
**Location:** `src/components/Navigation.tsx`

Top navigation bar with authentication.

**Features:**
- Logo and app title
- Active link highlighting
- Dashboard and Clusters links
- Logout button
- Responsive design

### 8. Providers.tsx
**Location:** `src/components/Providers.tsx`

React Query provider wrapper.

**Features:**
- QueryClient configuration
- 1-minute stale time
- Disabled refetch on window focus

## Pages

### Dashboard (/)
**Location:** `src/app/page.tsx`

Main dashboard showing overview and top clusters.

**Features:**
- Summary cards with key metrics
- 7-day trend chart
- Top 10 clusters by issue count
- Emerging issues (new clusters in past 7 days)
- Loading states for all sections
- Error handling with authentication fallback

### Clusters List (/clusters)
**Location:** `src/app/clusters/page.tsx`

Full cluster list with filtering.

**Features:**
- Advanced filters (category, subcategory, status, active/inactive, sort)
- URL-based filter state (bookmarkable URLs)
- Full cluster table with sorting
- Results count display
- Empty state for no results

### Cluster Detail (/clusters/[id])
**Location:** `src/app/clusters/[id]/page.tsx`

Detailed view of a single cluster.

**Features:**
- Cluster name and summary
- Key metrics cards (issues, customers, trend, status)
- Category and last seen metadata
- Status editor for PM updates
- Associated tickets table
- Back navigation button
- Loading and error states

## Layout & Authentication

### Layout (layout.tsx)
**Location:** `src/app/layout.tsx`

Root layout with providers and authentication.

**Features:**
- Auth provider wrapper
- React Query provider
- Navigation header
- Password prompt for unauthenticated users
- API client password injection

## API Integration

### API Client
**Location:** `src/lib/api.ts`

**Endpoints:**
- `GET /api/issues/summary` - Dashboard stats
- `GET /api/issues/trends` - Trend data
- `GET /api/clusters` - Cluster list (with filters)
- `GET /api/clusters/{id}` - Cluster detail
- `PATCH /api/clusters/{id}` - Update PM status/notes

**Authentication:**
All requests include `X-Dashboard-Password` header set from auth context.

## Styling

### Tailwind Configuration
**Location:** `tailwind.config.js`

**Custom Colors:**
- Severity: critical (red), high (orange), medium (yellow), low (blue)
- Trend: up (green), down (red), neutral (gray)

### Global Styles
**Location:** `src/app/globals.css`

**Custom Classes:**
- `.dashboard-card` - White card with border and shadow
- `.dashboard-header` - Page title styling
- `.section-title` - Section heading styling
- `.stat-value` / `.stat-label` - Metric display
- `.badge` variants - Status badges
- `.btn-primary` / `.btn-secondary` - Button styles

## State Management

### React Query
- Used for all API data fetching
- Cache invalidation on mutations
- Optimistic updates on cluster status changes
- 1-minute stale time
- Query keys: `['issues', 'summary']`, `['clusters', 'list']`, etc.

### Auth Context
**Location:** `src/lib/auth.tsx`

- Password stored in localStorage
- Auto-load on app init
- Logout clears password
- Password prompt component

## Development

### Running the App
```bash
cd C:\dev\uattendissuetrack\product-issue-miner\frontend
npm install
npm run dev
```

### Environment Variables
Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### TypeScript
All components use TypeScript with strict type checking. API types are defined in `src/lib/api.ts`.

## Responsive Design

All components are responsive with breakpoints:
- Mobile: 1 column layouts
- Tablet (md): 2 columns
- Desktop (lg): 3-4 columns

Tables scroll horizontally on mobile devices.
