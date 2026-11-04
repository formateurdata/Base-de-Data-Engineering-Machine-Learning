# Image Airflow du projet : les dépendances des DAG sont déclarées ici, aux versions de référence d'Airflow 3.3.2.
ARG CONTRAINTES=https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.13.txt

# Le provider HDFS exige gssapi et krb5, à compiler : le compilateur reste dans cette étape, hors de l'image finale.
FROM apache/airflow:3.3.2@sha256:e9982ad3f49a60418622e1baf80c34b0daf3fa5091a336cb5ee61f0cdd189371 AS compilation
ARG CONTRAINTES
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libkrb5-dev \
    && mkdir /wheels \
    && chown airflow /wheels
USER airflow
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels gssapi krb5 --constraint "$CONTRAINTES"

FROM apache/airflow:3.3.2@sha256:e9982ad3f49a60418622e1baf80c34b0daf3fa5091a336cb5ee61f0cdd189371
ARG CONTRAINTES
COPY requirements.txt /opt/airflow/requirements-dags.txt
RUN --mount=type=bind,from=compilation,source=/wheels,target=/wheels \
    pip install --no-cache-dir --find-links /wheels -r /opt/airflow/requirements-dags.txt --constraint "$CONTRAINTES"
COPY --chmod=755 demarrer.sh /opt/airflow/demarrer.sh
RUN mkdir -m 700 /opt/airflow/secrets
