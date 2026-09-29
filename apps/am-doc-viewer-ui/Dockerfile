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

# Generate missing Freezed files for git dependencies in pub-cache
RUN PUB_CACHE_DIR=$(find / -type d -name ".pub-cache" 2>/dev/null | grep -v "dart_tool" | head -n 1) && \
    if [ -z "$PUB_CACHE_DIR" ]; then PUB_CACHE_DIR=~/.pub-cache; fi && \
    echo "Pub cache is at $PUB_CACHE_DIR" && \
    MODERN_UI_DIR=$(find "$PUB_CACHE_DIR/git" -maxdepth 1 -type d -name "am-modern-ui-*" | head -n 1) && \
    if [ -n "$MODERN_UI_DIR" ]; then \
      for pkg in am_common am_design_system am_auth_ui am_library; do \
        if [ -d "$MODERN_UI_DIR/$pkg" ]; then \
          echo "Generating files for $pkg" && \
          cd "$MODERN_UI_DIR/$pkg" && \
          flutter pub get && \
          flutter pub run build_runner build --delete-conflicting-outputs || exit 1; \
        fi \
      done \
    else \
      echo "am-modern-ui not found in pub cache!" && exit 1; \
    fi
# Copy application code
COPY . .

# Build web application with correct base href
RUN flutter build web --release --base-href /doc-ui/

# Final stage: Serve with Nginx
FROM nginx:alpine
COPY --from=build-env /app/build/web /usr/share/nginx/html/doc-ui

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
