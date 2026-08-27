# Contexto de build = raiz del repo (ver docker-compose.yml). tokens.ts
# importa "../../../doc_app/design_tokens.json" (el hermano doc_app/ bajo
# la raiz, decision de G6: una unica fuente de verdad de diseño, sin
# duplicar el JSON dentro de frontend/) -- con el contexto limitado a
# ./frontend esa ruta no es alcanzable dentro de la imagen. Hallazgo real
# de G8 (criterio 17, primera vez que se construye esta imagen).
FROM node:20-slim AS build
WORKDIR /build
COPY doc_app ./doc_app
COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN cd frontend && npm install
COPY frontend ./frontend
# Build de produccion: rutas RELATIVAS al mismo origen que sirve el nginx
# de docker-compose.yml (infra/nginx/nginx.conf ya proxea /api/ y /ws/ al
# api-gateway) -- universales para cualquier dominio real, no hace falta
# parametrizarlas por despliegue. Vite hornea VITE_* en tiempo de BUILD,
# nunca en arranque -- sin esto (hallazgo real de G9, primera vez que se
# probo el flujo completo detras de nginx) la imagen arrancaba con los
# defaults de DESARROLLO de client.ts/useWsTopic.ts (http://localhost:8100)
# horneados dentro del JS, rotos para cualquier visitante real.
ENV VITE_API_BASE_URL=/api
ENV VITE_WS_BASE_URL=/ws
RUN cd frontend && npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /build/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
