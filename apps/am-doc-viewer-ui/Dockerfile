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
RUN find / -name "am-modern-ui-*" -type d 2>/dev/null | grep "/\.pub-cache/git/" | while read dir; do \
      for pkg in am_common am_design_system am_auth_ui am_library; do \
        if [ -d "$dir/$pkg" ]; then \
          echo "Generating files for $pkg" && \
          cd "$dir/$pkg" && \
          flutter pub get && \
          flutter pub run build_runner build --delete-conflicting-outputs || echo "Failed to build $pkg, continuing..."; \
        fi \
      done \
    done
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
