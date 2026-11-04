# Image HDFS native sur ARM et x86 : apache/hadoop n'est publiée qu'en amd64, et une JVM émulée est fragile sur Mac ARM.
FROM eclipse-temurin:17.0.20.1_1-jre-noble@sha256:b3e1d0486f09293b2455aed02d396d4b6b5ea9b0e8c7c065c297cfef453b0116 AS archive
ARG TARGETARCH
# Seul HDFS sert ici. Les dossiers yarn et mapreduce restent vides : les scripts Hadoop exigent leur présence.
RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl; \
    case "$TARGETARCH" in \
      arm64) fichier=hadoop-3.5.0-aarch64.tar.gz; somme=feaa20fea4709050ee993aae23b05720383a0d65aeda97c68d042e52564e8e77a83196a5a6973abdc690a1e600a73308ade56ccf9baeec231d1cf0810703430f ;; \
      amd64) fichier=hadoop-3.5.0.tar.gz; somme=04ab94496cc00c8b7a28d03f6308eff8d2a4e7f37a9da5e8e086e4d6fc990e7a94d661908f6a6136039536efb362614b8aecdef185b5fb8ed588f0b152c7aa16 ;; \
      *) echo "Architecture non prise en charge : $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 3 -o /tmp/hadoop.tar.gz "https://dlcdn.apache.org/hadoop/common/hadoop-3.5.0/$fichier" \
      || curl -fsSL --retry 3 -o /tmp/hadoop.tar.gz "https://archive.apache.org/dist/hadoop/common/hadoop-3.5.0/$fichier"; \
    echo "$somme  /tmp/hadoop.tar.gz" | sha512sum -c -; \
    mkdir /opt/hadoop; \
    tar -xzf /tmp/hadoop.tar.gz -C /opt/hadoop --strip-components=1; \
    rm -rf /opt/hadoop/share/doc /opt/hadoop/share/hadoop/yarn /opt/hadoop/share/hadoop/mapreduce /opt/hadoop/share/hadoop/tools; \
    mkdir /opt/hadoop/share/hadoop/yarn /opt/hadoop/share/hadoop/mapreduce

FROM eclipse-temurin:17.0.20.1_1-jre-noble@sha256:b3e1d0486f09293b2455aed02d396d4b6b5ea9b0e8c7c065c297cfef453b0116
RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl procps; \
    rm -rf /var/lib/apt/lists/*; \
    useradd --create-home hadoop; \
    mkdir -p /hadoop/dfs/name /hadoop/dfs/data; \
    chown -R hadoop:hadoop /hadoop
COPY --from=archive /opt/hadoop /opt/hadoop
COPY core-site.xml hdfs-site.xml /opt/hadoop/etc/hadoop/
ENV HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    HADOOP_LOG_DIR=/tmp/hadoop-logs \
    PATH=/opt/hadoop/bin:/opt/hadoop/sbin:$PATH
USER hadoop
