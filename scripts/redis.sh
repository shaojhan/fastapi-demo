#!/bin/bash
# Redis container management (Podman)

case "${1:-start}" in
  start)
    podman run -d \
      --name redis \
      -p 6379:6379 \
      docker.io/redis:7-alpine
    echo "Redis started on localhost:6379"
    ;;
  stop)
    podman stop redis && podman rm redis
    echo "Redis stopped"
    ;;
  restart)
    podman stop redis && podman rm redis
    "$0" start
    ;;
  logs)
    podman logs -f redis
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs}"
    ;;
esac
