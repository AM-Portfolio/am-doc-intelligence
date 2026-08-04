# Multi-stage build for Flutter Web
ARG BASE_REGISTRY=""
FROM ${BASE_REGISTRY}am-flutter-base:latest AS build-env

ARG GITHUB_PACKAGES_USERNAME
ARG GITHUB_PACKAGES_TOKEN

# Clone the private dependencies repository into /am-modern-ui
RUN git clone https://${GITHUB_PACKAGES_USERNAME}:${GITHUB_PACKAGES_TOKEN}@github.com/AM-Portfolio/am-modern-ui.git /am-modern-ui

# Resolve dependencies and generate code for the shared modules in topological order
WORKDIR /am-modern-ui/am_library
RUN flutter pub get

WORKDIR /am-modern-ui/am_design_system
RUN flutter pub get && dart run build_runner build --delete-conflicting-outputs

WORKDIR /am-modern-ui/am_common
RUN flutter pub get && dart run build_runner build --delete-conflicting-outputs

WORKDIR /am-modern-ui/am_auth_ui
RUN flutter pub get && dart run build_runner build --delete-conflicting-outputs

# Set working directory for the main application
WORKDIR /app

# Copy and build
COPY . .
RUN flutter pub get
# Build web application with correct base href
RUN flutter build web --release --base-href /doc-ui/

# Final stage: Serve with Nginx
FROM nginx:alpine
COPY --from=build-env /app/build/web /usr/share/nginx/html/doc-ui

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
