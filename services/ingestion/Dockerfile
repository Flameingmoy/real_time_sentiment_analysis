# Data Ingestion Service Dockerfile

# Stage 1: Builder image to compile the Go application
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy and download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code into the builder image
COPY . .

# Create static Go binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /app/ingestion-service .

# Stage 2: Final Image for running the service
FROM alpine:latest

WORKDIR /app

# Copy the compiled binary from the builder stage
COPY --from=builder /app/ingestion-service .
COPY config.yaml .

# Expose 8080 to access the data ingestion service
EXPOSE 8080

# Placeholder command, to be replaced after the service is implemented
CMD ["./ingestion-service"]
