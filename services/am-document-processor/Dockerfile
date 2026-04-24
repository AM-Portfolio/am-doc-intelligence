# ===============================
# Runtime Image
# ===============================
FROM eclipse-temurin:17-jre-jammy

WORKDIR /app

# Copy JAR pre-built by the CI runner
# Note: The JAR is built in target/ because it's a single-module project
COPY target/am-processor-*.jar app.jar

# Install curl for healthcheck
RUN apt-get update && \
  apt-get install -y curl && \
  rm -rf /var/lib/apt/lists/* && \
  ln -sf /usr/share/zoneinfo/Asia/Kolkata /etc/localtime

# Environment variables
ENV SPRING_PROFILES_ACTIVE=docker
ENV TZ=Asia/Kolkata

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=5 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
