# ===============================
# Stage 1: Build with Maven
# ===============================
FROM eclipse-temurin:17-jdk-jammy AS builder

WORKDIR /app

# Build arguments for GitHub Packages auth
ARG GITHUB_PACKAGES_USERNAME
ARG GITHUB_PACKAGES_TOKEN

# Copy Maven Wrapper and configuration
COPY .mvn/ .mvn
COPY mvnw pom.xml mvn_settings.xml ./

# Convert line endings for mvnw just in case
RUN sed -i 's/\r$//' mvnw
RUN chmod +x mvnw

# Download dependencies (using settings for auth)
RUN ./mvnw dependency:go-offline -s mvn_settings.xml

# Copy source code
COPY src ./src

# Build the JAR
RUN ./mvnw clean package -DskipTests -s mvn_settings.xml


# ===============================
# Stage 2: Runtime Image
# ===============================
FROM eclipse-temurin:17-jre-jammy

WORKDIR /app

# Copy JAR from builder stage
COPY --from=builder /app/target/am-processor-*.jar app.jar

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
