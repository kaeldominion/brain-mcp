FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
RUN addgroup -g 10001 brain && adduser -u 10001 -G brain -D brain
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=brain:brain /app/.next/standalone ./
COPY --from=build --chown=brain:brain /app/.next/static ./.next/static
USER brain
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["wget", "-qO-", "http://127.0.0.1:3000/api/healthz"]
CMD ["node", "server.js"]
