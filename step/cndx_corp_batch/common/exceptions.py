class BatchError(Exception):
    """
    業務的に想定されたエラー
    ・入力不備
    ・外部データ欠損
    ・業務ルール違反
    """
    pass


class RetryableError(BatchError):
    """
    再実行可能なエラー
    ・一時的なネットワーク障害
    ・外部APIの一時エラー
    ・ロック競合
    """
    pass