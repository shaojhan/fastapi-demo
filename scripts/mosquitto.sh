#!/bin/bash
# Mosquitto container management (Podman)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

case "${1:-start}" in
  start)
    podman run -d \
      --name mosquitto \
      -p 1883:1883 \
      -v "$PROJECT_DIR/mosquitto/config:/mosquitto/config:ro" \
      docker.io/eclipse-mosquitto:2
    echo "Mosquitto started on localhost:1883"
    ;;
  stop)
    podman stop mosquitto && podman rm mosquitto
    echo "Mosquitto stopped"
    ;;
  restart)
    podman stop mosquitto && podman rm mosquitto
    "$0" start
    ;;
  logs)
    podman logs -f mosquitto
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs}"
    ;;
esac
