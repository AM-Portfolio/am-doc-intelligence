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

# Generate missing Freezed files by copying out of cache to avoid read-only issues
RUN PUB_CACHE_DIR=$(find / -type d -name ".pub-cache" 2>/dev/null | grep -v "dart_tool" | head -n 1) && \
    if [ -z "$PUB_CACHE_DIR" ]; then PUB_CACHE_DIR=~/.pub-cache; fi && \
    echo "Pub cache is at $PUB_CACHE_DIR" && \
    MODERN_UI_DIR=$(find "$PUB_CACHE_DIR/git" -maxdepth 1 -type d -name "am-modern-ui-*" | head -n 1) && \
    if [ -n "$MODERN_UI_DIR" ]; then \
      cp -r "$MODERN_UI_DIR" /tmp/am-modern-ui && \
      for pkg in am_common am_design_system am_auth_ui am_library; do \
        if [ -d "/tmp/am-modern-ui/$pkg" ]; then \
          echo "Generating files for $pkg" && \
          cd "/tmp/am-modern-ui/$pkg" && \
          flutter pub get && \
          flutter pub run build_runner build --delete-conflicting-outputs || exit 1; \
        fi \
      done \
    else \
      echo "am-modern-ui not found in pub cache!" && exit 1; \
    fi

# Use the generated files in /tmp by adding dependency_overrides to pubspec.yaml
RUN echo "" >> pubspec.yaml && \
    echo "dependency_overrides:" >> pubspec.yaml && \
    echo "  am_common:" >> pubspec.yaml && \
    echo "    path: /tmp/am-modern-ui/am_common" >> pubspec.yaml && \
    echo "  am_design_system:" >> pubspec.yaml && \
    echo "    path: /tmp/am-modern-ui/am_design_system" >> pubspec.yaml && \
    echo "  am_auth_ui:" >> pubspec.yaml && \
    echo "    path: /tmp/am-modern-ui/am_auth_ui" >> pubspec.yaml && \
    echo "  am_library:" >> pubspec.yaml && \
    echo "    path: /tmp/am-modern-ui/am_library" >> pubspec.yaml && \
    flutter pub get
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
