#!/bin/bash

VERSION=$1
TARGETPJ=$2
ENV=$3

DOCKERFILE="Dockerfile.fluent"

# Docker イメージのビルド
docker build -f $DOCKERFILE -t cndx-corp-fluent-bit:$VERSION .

# Dockerイメージのタグ付け
echo "Tagging Docker image as: data.ts.tdh.tepcube.jp:10060/$TARGETPJ/cndx-corp-fluent-bit:$VERSION"
docker tag cndx-corp-fluent-bit:$VERSION data.ts.tdh.tepcube.jp:10060/$TARGETPJ/cndx-corp-fluent-bit:$VERSION

# Dockerレジストリへのログイン
echo "Logging in to Docker registry..."
docker login https://data.ts.tdh.tepcube.jp:10060

# Dockerイメージをリモートレジストリにプッシュ
echo "Pushing Docker image to registry..."
docker push data.ts.tdh.tepcube.jp:10060/$TARGETPJ/cndx-corp-fluent-bit:$VERSION

echo "Docker image $VERSION has been pushed successfully."

