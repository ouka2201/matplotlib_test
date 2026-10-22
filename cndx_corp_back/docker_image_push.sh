#!/bin/bash
export HD_USER="hd-dev-user01"
export HD_PASS="LRd+Epi%y3"
export EP_USER="ep-dev user01"
export EP_PASS='bLiZ!HiYK6'

# 引数チェック
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "$0 引数不足"
  exit 1
fi

PORT=$1
TARGETPJ=$2
VERSION=$3

# Docker イメージのビルド
echo "バックDocker イメージのビルド: $VERSION"
docker build -f Dockerfile -t cndx-corp-back:$VERSION .

# Dockerイメージのタグ付け
echo "Dockerイメージのタグ付け: data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/cndx-corp-back:$VERSION"
docker tag cndx-corp-back:$VERSION data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/cndx-corp-back:$VERSION
docker tag cndx-corp-back:$VERSION data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/cndx-corp-back:latest

# Dockerレジストリへのログイン
echo "Dockerレジストリへのログイン"
# docker login https://data.ts.tdh.tepcube.jp:$PORT
# docker login http://data.ts.tdh.tepcube.jp:10060 -u "hd-dev-user01" -p "LRd+Epi%y3"
# docker login http://data.ts.tdh.tepcube.jp:10140 -u 'ep-dev user01' -p 'bLiZ!HiYK6'
case "$PORT" in
  10060)
    USER="$HD_USER"
    PASS="$HD_PASS"
    ;;
  10140)
    USER="$EP_USER"
    PASS="$EP_PASS"
    ;;
  *)
    echo "Unknown port"
    exit 1
    ;;
esac

docker login "http://data.ts.tdh.tepcube.jp:${PORT}" -u "$USER" -p "$PASS"

# Dockerイメージをリモートレジストリにプッシュ
echo "Dockerイメージをリモートレジストリにプッシュ"
docker push data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/cndx-corp-back:$VERSION
docker push data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/cndx-corp-back:latest

echo "Docker image $VERSION has been pushed successfully."

# ./docker_image_push_ep.sh 0.0.1 ep_stage cndx_corp_stg
# ./docker_image_push_ep.sh 0.0.1 ep_prod cndx_corp_step3_prod
# ./docker_image_push_ep.sh 10060 cndx_corp_step3_stg 0.1

# ./docker_image_push.sh 10140 cndx_corp_step3_maint latest

# 引数の明記　version命名ルール シェル実行する前提条件　手順書完備してから展開、検証

