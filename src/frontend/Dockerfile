FROM node:25.8 AS builder
WORKDIR /app

RUN npm install -g pnpm@10.33.0

COPY acc/package.json acc/pnpm-lock.yaml* ./

RUN pnpm install --frozen-lockfile --prod=false

COPY acc/ .

ARG VITE_BASE_API_URL

RUN echo "VITE_BASE_API_URL=${VITE_BASE_API_URL}" > .env.production

RUN pnpm build

FROM node:25.8-slim
WORKDIR /app

RUN npm install -g serve@14.2.6

COPY --from=builder /app/dist ./dist

EXPOSE 3000

USER node

CMD ["serve", "-s", "dist"]
