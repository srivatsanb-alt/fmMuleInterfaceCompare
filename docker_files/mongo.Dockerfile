FROM mongo:7.0

# Copy the entrypoint script from misc folder
COPY misc/mongo-init/entrypoint.sh /docker-entrypoint-initdb.d/entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /docker-entrypoint-initdb.d/entrypoint.sh
