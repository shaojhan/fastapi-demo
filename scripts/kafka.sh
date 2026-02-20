#!/bin/bash
# Kafka container management (Podman)

case "${1:-start}" in
  start)
    podman run -d \
      --name kafka \
      -p 9092:9092 \
      -e KAFKA_NODE_ID=1 \
      -e KAFKA_PROCESS_ROLES=broker,controller \
      -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 \
      -e KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093 \
      -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
      -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT \
      -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
      -e CLUSTER_ID=MkU3OEVBNTcwNTJENDM2Qk \
      docker.io/apache/kafka:latest
    echo "Kafka started on localhost:9092"
    ;;
  stop)
    podman stop kafka && podman rm kafka
    echo "Kafka stopped"
    ;;
  restart)
    podman stop kafka && podman rm kafka
    "$0" start
    ;;
  logs)
    podman logs -f kafka
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs}"
    ;;
esac
