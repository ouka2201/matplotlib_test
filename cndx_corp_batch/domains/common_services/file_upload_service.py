import os
from pathlib import Path
import tempfile
from typing import BinaryIO, Dict, Iterable, Optional, Union


class FileUploadService:
    def execute(
        self,
        local_file_path: str,
        upload_target_path: str,
        logger: Optional[object] = None,
    ):
        """
        Batch向けファイルアップロードサービス

        Args:
            input_file_path: アップロード元ファイル（Path）
            upload_target_dir: アップロード先ディレクトリ（Path）
        """
        try:
            if logger:
                logger.debug(
                    "upload start: src=%s dst_dir=%s",
                    local_file_path,
                    upload_target_path,
                )

            if not os.path.exists(local_file_path):
                raise FileNotFoundError(local_file_path)

            # アップロード先フォルダ作成
            Path(upload_target_path).mkdir(parents=True, exist_ok=True)

            # 保存処理（既存ロジック）
            self._save_file(local_file_path, upload_target_path)

            logger.info(
                f"アップロード完了 file={os.path.basename(local_file_path)}"
            )
            return upload_target_path
        except Exception:
            if logger:
                logger.exception("ファイルアップロード処理が失敗しました。")
            raise
    
    def _save_file(self, local_file_path, put_path):
        put_out = self._put_file(local_file_path, put_path)
        if put_out.returncode != 0:
            msg = (
                f'put_file is failed. '
                f'file name is {local_file_path}. '
                f'put path is {put_path}. '
                f'stdout is {put_out}'
            )
            raise Exception(msg)

        return True
    
    def _put_file(self, _local_path, _put_path):
        import subprocess

        out = subprocess.run(["hadoop", "fs", "-put", "-f", _local_path, _put_path],
                            capture_output=True)
        return out

    def get_upload_path(
        self,
        target_path_parts: Iterable[str] | Dict[str, str],
        put_path: str = "corp",
    ) -> Path:
        """
        Batch向けアップロードパス生成

        Args:
            target_path_parts:
                ["2026", "01", "report"] など
                or {"year": "2026", "month": "01"}
            put_path: 論理ルート名（例: corp）

        Returns:
            Path
        """

        if isinstance(target_path_parts, dict):
            # dictは順序保証が前提（Python3.7+）
            parts = list(target_path_parts.values())
        else:
            parts = list(target_path_parts)

        upload_path = self.base_path / put_path
        for p in parts:
            upload_path /= str(p)

        return upload_path
    
    def pathjoin(self, *_path_list):

        safe_paths = []
        for _path in _path_list:
            if not isinstance(_path, str):
                continue  # 無効な値をスキップ
            if _path.startswith('/'):
                _path = _path[1:]
            if _path.endswith('/') and not _path.endswith('://'):
                _path = _path[:-1]
            safe_paths.append(_path)

        return os.path.join(*safe_paths)
    
    def write_stream_to_temp_file(
        self,
        stream: Union[bytes, BinaryIO],
        suffix: str,
    ) -> str:
        """
        PDF stream / bytes を一時ファイルに書き出す
        Returns: local file path
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            if hasattr(stream, "read"):
                f.write(stream.read())
            else:
                f.write(stream)
            return f.name