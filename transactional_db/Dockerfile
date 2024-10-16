# Use the official PostgreSQL base image
FROM postgres:14

# Set environment variables for PostgreSQL credentials
ENV POSTGRES_USER=guest
ENV POSTGRES_PASSWORD=1234
ENV POSTGRES_DB=transact_db

# Copy the initialization SQL file to the Docker image
# The /docker-entrypoint-initdb.d/ directory is automatically scanned and executed at container startup
COPY init.sql /docker-entrypoint-initdb.d/

# Expose the PostgreSQL port
EXPOSE 5432
