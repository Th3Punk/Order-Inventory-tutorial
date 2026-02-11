FROM apache/flink:1.19

ARG FLINK_KAFKA_CONNECTOR_VERSION=3.3.0-1.19
ARG KAFKA_CLIENTS_VERSION=3.5.1

RUN apt-get update && apt-get install -y python3 python3-pip curl openjdk-17-jdk \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && python3 -m pip install --no-cache-dir --upgrade pip uv \
    && curl -fsSL -o /opt/flink/lib/flink-connector-kafka-${FLINK_KAFKA_CONNECTOR_VERSION}.jar \
        https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/${FLINK_KAFKA_CONNECTOR_VERSION}/flink-connector-kafka-${FLINK_KAFKA_CONNECTOR_VERSION}.jar \
    && curl -fsSL -o /opt/flink/lib/kafka-clients-${KAFKA_CLIENTS_VERSION}.jar \
        https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/${KAFKA_CLIENTS_VERSION}/kafka-clients-${KAFKA_CLIENTS_VERSION}.jar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/stream-job

COPY pyproject.toml /opt/stream-job/pyproject.toml
COPY app /opt/stream-job/app

# Force uv to use the image Python, not a root-owned downloaded interpreter.
ENV UV_PYTHON_PREFERENCE=system

RUN uv venv /opt/stream-job/.venv --python /usr/bin/python3 \
  && UV_PROJECT_ENVIRONMENT=/opt/stream-job/.venv uv sync --preview-features extra-build-dependencies \
  && /opt/stream-job/.venv/bin/python -c "import pkg_resources" \
  && chown -R flink:flink /opt/stream-job \
  && chmod -R a+rx /opt/stream-job/.venv

ENV PYTHONPATH=/opt/stream-job \
    PYFLINK_CLIENT_EXECUTABLE=/opt/stream-job/.venv/bin/python \
    PYFLINK_PYTHON_EXECUTABLE=/opt/stream-job/.venv/bin/python

CMD ["flink", "run", "-m", "jobmanager:8081", "-py", "/opt/stream-job/app/job.py", "-pyexec", "/opt/stream-job/.venv/bin/python", "-pyclientexec", "/opt/stream-job/.venv/bin/python"]
