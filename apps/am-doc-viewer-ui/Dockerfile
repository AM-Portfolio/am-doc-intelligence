# Multi-stage build for Flutter Web
ARG BASE_REGISTRY=""
FROM ${BASE_REGISTRY}am-flutter-base:latest AS build-env

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching optimisation)
COPY pubspec.yaml .
ARG GITHUB_PACKAGES_TOKEN
RUN git config --global url."https://x-access-token:${GITHUB_PACKAGES_TOKEN}@github.com/".insteadOf "https://github.com/"
RUN flutter pub get

# Copy application code
COPY . .

# Build web application with correct base href
RUN flutter build web --release --base-href /doc-ui/ --web-renderer canvaskit

# Final stage: Serve with Nginx
FROM nginx:alpine
COPY --from=build-env /app/build/web /usr/share/nginx/html/doc-ui

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
