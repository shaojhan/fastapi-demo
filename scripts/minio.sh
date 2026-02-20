#!/bin/bash
# MinIO container management (Podman)

case "${1:-start}" in
  start)
    podman run -d \
      --name minio \
      -p 9000:9000 \
      -p 9001:9001 \
      -e MINIO_ROOT_USER=minioadmin \
      -e MINIO_ROOT_PASSWORD=minioadmin \
      docker.io/minio/minio:latest \
      server /data --console-address ":9001"
    echo "MinIO started — API: localhost:9000, Console: localhost:9001"
    ;;
  stop)
    podman stop minio && podman rm minio
    echo "MinIO stopped"
    ;;
  restart)
    podman stop minio && podman rm minio
    "$0" start
    ;;
  logs)
    podman logs -f minio
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs}"
    ;;
esac
