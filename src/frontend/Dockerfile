FROM node:26.10.0 AS builder
WORKDIR /app

RUN npm install -g pnpm@12.8.1

COPY acc/package.json acc/pnpm-lock.yaml acc/pnpm-workspace.yaml ./

RUN pnpm install --frozen-lockfile --prod=false

COPY acc/ .

ARG VITE_BASE_API_URL

RUN echo "VITE_BASE_API_URL=${VITE_BASE_API_URL}" > .env.production

RUN pnpm build

# The edge Nginx serves the built frontend; its configuration is mounted by Compose.
FROM nginx:1.31.6

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html
