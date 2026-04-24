# Multi-stage build for Flutter Web
FROM am-flutter-base:latest AS build-env

# Set working directory
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
