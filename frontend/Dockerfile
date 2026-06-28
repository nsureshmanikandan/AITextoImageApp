# =============================================================================
# VernacularCast — Frontend Dockerfile
# Multi-stage build: Node 20 (build) → Nginx Alpine (serve)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build the React / Vite application
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Install build dependencies for native node modules (if any)
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy dependency manifests first for Docker layer caching
COPY package*.json ./

# Install all dependencies (including devDependencies needed for build)
RUN npm ci

# Copy application source
COPY . .

# Build the production bundle
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Serve with Nginx
# ---------------------------------------------------------------------------
FROM nginx:alpine AS production

# Remove default Nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our SPA-aware Nginx config
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf

# Copy the compiled React bundle from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP
EXPOSE 80

# Nginx runs in the foreground by default
CMD ["nginx", "-g", "daemon off;"]
