# ---------------------------------------------------------------------------
# MemoryOS frontend — React + Vite production bundle behind nginx
#
# Build:
#   docker build -t memoryos-frontend -f frontend/Dockerfile .
# Run:
#   docker run -p 8080:80 memoryos-frontend
#
# Two things matter here and both are easy to get wrong:
#   1. VITE_API_BASE_URL is baked in at BUILD time (Vite inlines env into the
#      bundle). Point it at wherever the backend is reachable FROM THE BROWSER,
#      not from inside the container.
#   2. The app uses BrowserRouter, so nginx must fall back to index.html or a
#      deep link like /governance returns 404. See nginx.conf.
# ---------------------------------------------------------------------------

FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Baked at build time. Same-origin (empty string) works when the API is served
# from the same host — e.g. via a reverse proxy. Set an absolute URL when the
# backend lives on a different origin.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
