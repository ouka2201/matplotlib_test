import time

def retry(func, times=3, delay=5):
    for i in range(times):
        try:
            return func()
        except Exception:
            if i == times - 1:
                raise
            time.sleep(delay)
