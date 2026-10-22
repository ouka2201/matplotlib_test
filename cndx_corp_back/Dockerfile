# 公式 Python イメージをベースイメージとして使用
FROM python:3.13.1-slim

# 作業ディレクトリ設定
WORKDIR /app/cndx_corp_back

# 必要なシステム依存関係をインストール
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    wget \
    # curl \
    tar \
    # vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------- Java & Hadoop セットアップ（めったに変わらない部分） ----------
# OpenJDK 11
ENV JAVA_VERSION=11.0.20
ENV JAVA_HOME=/opt/jdk
ENV PATH="$JAVA_HOME/bin:$PATH"

RUN wget https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.20+8/OpenJDK11U-jdk_x64_linux_hotspot_${JAVA_VERSION}_8.tar.gz -P /tmp/ \
    && tar -xvzf /tmp/OpenJDK11U-jdk_x64_linux_hotspot_${JAVA_VERSION}_8.tar.gz -C /opt/ \
    && rm /tmp/OpenJDK11U-jdk_x64_linux_hotspot_${JAVA_VERSION}_8.tar.gz \
    && ln -s /opt/jdk-${JAVA_VERSION}+8 $JAVA_HOME

# Hadoop
ENV HADOOP_VERSION=3.3.5
RUN wget https://downloads.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz \
    && tar -xvzf hadoop-${HADOOP_VERSION}.tar.gz -C /opt/ \
    && rm hadoop-${HADOOP_VERSION}.tar.gz \
    && ln -s /opt/hadoop-${HADOOP_VERSION} /opt/hadoop

# 環境変数の設定 (Hadoop)
ENV HADOOP_HOME=/opt/hadoop
ENV PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
ENV CLASSPATH=$CLASSPATH:/opt/bdfs/bluedata-dtap.jar
ENV HADOOP_CLASSPATH=$HADOOP_CLASSPATH:/opt/bdfs/bluedata-dtap.jar

# ---------- Python 関連（よく変わる部分） ----------
# 先に requirements.txt だけコピー → キャッシュ効かせる
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# core-site.xml を Hadoop 設定フォルダにコピー
COPY core-site.xml /opt/hadoop/etc/hadoop/core-site.xml

# プロジェクトファイルコピー
COPY . .

# アプリ用の環境変数（よく変更する部分）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py \
    # FLASK_ENV=maint \
    PYTHONPATH=/app \
    # DATABASE_URL=postgresql://postgres:EYr^3NmPBq@postgresql.cndx-corp-maint.svc.cluster.local:5432/epdb \
    LOG_LEVEL=DEBUG \
    GUNICORN_CMD_ARGS="--workers=4 --worker-class=gevent --timeout=1200 --max-requests=500"

# フォルダ作成
RUN mkdir -p tmp/resources/hyper/

# ポート公開
EXPOSE 5000

# 起動コマンド
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:application"]
