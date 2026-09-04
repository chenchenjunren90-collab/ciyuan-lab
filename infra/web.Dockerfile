FROM docker.1panel.live/library/node:22-alpine AS builder

WORKDIR /build
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY apps/web ./
RUN npm run build

FROM docker.1panel.live/library/nginx:1.27-alpine
COPY infra/nginx.production.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html
EXPOSE 80
