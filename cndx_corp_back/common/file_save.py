
import os
import re


def save_file(local_file_path, put_path):
    
    put_out = put_file(local_file_path, put_path)
    if put_out.returncode != 0:
        msg = f'put_file is failed. file name is {local_file_path}. put path is {put_path}. stdout is {put_out}'
        raise Exception(msg)

    return True

def put_file(_local_path, _put_path):
    import subprocess

    out = subprocess.run(["hadoop", "fs", "-put", "-f", _local_path, _put_path],
                         capture_output=True)
    return out

def get_put_path(*_path_list):
    import os
    _path_list = [
        _path[1:] if _path[0] == '/' else _path for _path in _path_list
    ]
    _path_list = [
        _path[:-1] if ((_path[-1] == '/') and (_path[-3:] != '://')) else _path
        for _path in _path_list
    ]
    return os.path.join(*_path_list)

def ls_volume(_path):
    import subprocess
    ls_out = subprocess.run(["hdfs", "dfs", "-ls", "-R", _path],
                            encoding='utf-8',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if ls_out.returncode != 0:
        msg = f'hdfs dfs -ls command is failed. path is {_path}. stdout is {ls_out.stdout}. stderr is {ls_out.stderr}'
        raise Exception(msg)
    exist_files = [_line.split() for _line in ls_out.stdout.splitlines()[0:] if _line.startswith("-rw-")]
    exist_files = [os.path.basename(_line[-1]) for _line in exist_files]
    return exist_files

def filter_target_file(file_name):
    import json
    import re
    filter_str = "[]"
    filter_list = _load_json_to_list(filter_str)
    try:
        for filter_str in filter_list:
            if file_name.lower().startswith(filter_str.lower()):
                return True
    except Exception as e:
        # logger.error(f'error in filter list area. error message : {e}')
        raise e

    return False

# VariablesのJson文字列からlistに変換する
def _load_json_to_list(_json_file):
    import json
    try:
        target_list = json.loads(_json_file)
    except Exception as e:
        # logger.error(f'error in target list area. error message : {e}')
        raise e

    return target_list

def make_folder(_full_path):
    import subprocess
    
    out = subprocess.run(["hdfs", "dfs", "-mkdir", "-p", _full_path],
                         capture_output=True)
    return out

def pathjoin(*_path_list):

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

def get_next_filename(filename: str, exist_files):
    """同じファイル名がある場合、枝番を取得し新しい名前を生成する"""
    base, ext = os.path.splitext(filename)  # ファイル名と拡張子を分割
    pattern = re.compile(rf"^{re.escape(base)}(?:_(\d+))?{re.escape(ext)}$")

    # 既存ファイルの中で、同じベース名を持つファイルの枝番を取得
    existing_numbers = []
    for file in exist_files:
        match = pattern.match(file)
        if match:
            num = match.group(1)
            existing_numbers.append(int(num)) if num else existing_numbers.append(0)

    # 新しい枝番を決定（既存枝番の最大値+1）
    new_suffix = max(existing_numbers, default=0) + 1
    new_filename = f"{base}_{new_suffix}{ext}" if new_suffix > 0 else filename

    return new_filename