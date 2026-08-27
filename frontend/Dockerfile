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
RUN cd frontend && npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /build/frontend/dist /usr/share/nginx/html
EXPOSE 80
