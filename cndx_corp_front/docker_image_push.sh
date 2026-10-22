#!/bin/bash
export HD_USER="hd-dev-user01"
export HD_PASS="LRd+Epi%y3"
export EP_USER="ep-dev user01"
export EP_PASS='bLiZ!HiYK6'

# 引数が指定されていない場合、エラーメッセージを表示
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
  echo "$0 引数不足"
  exit 1
fi

SVC=$1
PORT=$2
TARGETPJ=$3
VERSION=$4

# 環境に応じた Dockerfile の選択
if [ "$SVC" = "remix" ]; then
  DOCKERFILE="Dockerfile.remix"
  SVC="cndx-corp-front"
elif [ "$SVC" = "nginx" ]; then
  DOCKERFILE="Dockerfile.nginx"
  SVC="cndx-corp-nginx"
else
  echo "引数不正"
  exit 1
fi

# Dockerイメージのビルド
echo "Dockerイメージのビルド: $VERSION"
docker build -f $DOCKERFILE -t $SVC:$VERSION .

# Dockerイメージのタグ付け
echo "Dockerイメージのタグ付け: data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/$SVC:$VERSION"
docker tag $SVC:$VERSION data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/$SVC:$VERSION
docker tag $SVC:$VERSION data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/$SVC:latest

# Dockerレジストリへのログイン
echo "Dockerレジストリへのログイン..."
# docker login https://data.ts.tdh.tepcube.jp:$PORT
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
echo "Dockerイメージをリモートレジストリにプッシュ..."
docker push data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/$SVC:$VERSION
docker push data.ts.tdh.tepcube.jp:$PORT/$TARGETPJ/$SVC:latest

echo "Docker image $VERSION has been pushed successfully."

# ./docker_image_push_ep.sh 1.0.0 remix_prod cndx_corp_step3_prod
# ./docker_image_push_ep.sh 1.0.0 remix_stg cndx_corp_stg
# ./docker_image_push_ep.sh 1.0.0 nginx_stage cndx_corp_stage
# ./docker_image_push_ep.sh 1.0.0 nginx_prod cndx_corp_step3_prod

# ./docker_image_push.sh remix 10140 cndx_corp_step3_maint latest
# ./docker_image_push.sh nginx 10140 cndx_corp_step3_maint latest



