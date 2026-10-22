import io
import subprocess
import traceback
import zipfile

from flask import abort


def download(path: str | list[str], logger=None) -> tuple[io.BytesIO | str]:
    """HDFSファイルパスに格納されているファイルを BytesIO 取得（複数可）"""

    if logger:
        logger.debug(f"hdfs_file_path★★{path}")

    if isinstance(path, list):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(
            zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            for p in path:
                file_stream, file_nm = get_from_hdfs(p, logger=logger)
                zf.writestr(file_nm, file_stream.getvalue())
            zip_buffer.seek(0)
        return zip_buffer, "pack.zip"
    else:
        return get_from_hdfs()


def get_from_hdfs(path, logger=None) -> tuple[io.BytesIO | str]:
    try:
        # HDFSからファイル内容を取得
        process = subprocess.run(
            ["hadoop", "fs", "-cat", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        file_stream = io.BytesIO(process.stdout)

        file_name: str = path.split("/")[-1]  # ファイル名を取得
        print(file_name)

        return file_stream, file_name
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(traceback.format_exc())
        abort(500)

