# Builder stage - Install dependencies and build Next.js application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
# Note: paths are relative to repo root for Railway builds
COPY product-issue-miner/frontend/package*.json ./
RUN npm ci

# Copy application code
COPY product-issue-miner/frontend/ .

# Build Next.js application with standalone output
RUN npm run build

# Runner stage - Optimized production image
FROM node:20-alpine AS runner

WORKDIR /app

# Set environment variables
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy built application from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Set ownership to non-root user
RUN chown -R nextjs:nodejs /app

USER nextjs

# Expose port
EXPOSE 3000

# Set port environment variable
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})" || exit 1

# Start application
CMD ["node", "server.js"]
