import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta

BASE_LOG_DIR = "/bd-fs-mnt/TenantShare/log/batch"
RETENTION_DAYS = 30

def cleanup_old_logs(base_dir: str, retention_days: int):
    now = datetime.now()
    expire_before = now - timedelta(days=retention_days)

    for batch_name in os.listdir(base_dir):
        batch_path = os.path.join(base_dir, batch_name)
        if not os.path.isdir(batch_path):
            continue

        for date_dir in os.listdir(batch_path):
            date_path = os.path.join(batch_path, date_dir)

            if not os.path.isdir(date_path):
                continue

            try:
                # フォルダ名が YYYYMMDD 前提
                log_date = datetime.strptime(date_dir, "%Y%m%d")
            except ValueError:
                continue  # 想定外の名前は無視

            if log_date < expire_before:
                shutil.rmtree(date_path)

# def cleanup_all_logs(base_dir: str):
#     for name in os.listdir(base_dir):
#         path = os.path.join(base_dir, name)
#         if os.path.isdir(path):
#             shutil.rmtree(path)
#         else:
#             os.remove(path)

def cleanup_all_logs(base_dir: str, keep_dir: str):
    base = Path(base_dir).resolve()
    keep = Path(keep_dir).resolve()

    for path in base.iterdir():
        # keep_dir 自体 or keep_dir の祖先は削除しない
        if path == keep or path in keep.parents:
            continue

        # keep_dir の配下も削除しない
        if keep.is_relative_to(path):
            continue

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

def delete_old_logs(base_dir: str, cutoff_date: str):
    """
    cutoff_date: 'YYYYMMDD' 例: '20260202'
    """
    cutoff = datetime.strptime(cutoff_date, "%Y%m%d").timestamp()
    base = Path(base_dir)

    for path in base.rglob("*.log"):
        try:
            mtime = path.stat().st_mtime
            if mtime < cutoff:
                path.unlink()
        except Exception as e:
            # ログ削除失敗しても batch を落とさない
            print(f"Failed to delete {path}: {e}")