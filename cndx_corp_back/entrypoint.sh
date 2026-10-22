#!/bin/bash

# 日付付きのログファイルを作成
LOG_FILE="/logs/kubectl_$(date '+%Y%m%d_%H%M%S').log"

# ログを退避
kubectl logs cndx-corp-back-* > "$LOG_FILE"

# Gunicorn を起動
exec gunicorn --bind 0.0.0.0:5000 wsgi:application