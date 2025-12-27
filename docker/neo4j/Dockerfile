FROM neo4j:5.13.0-community

# Neo4j community edition with admin tools for backup/restore
# Install any additional utilities if needed
USER root

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

USER neo4j

# Default healthcheck is defined in docker-compose.yml
# Ensure backup and data directories exist
RUN mkdir -p /backups /var/lib/neo4j/data

EXPOSE 7474 7687

ENTRYPOINT ["/sbin/tini", "-g", "--"]
CMD ["neo4j"]
