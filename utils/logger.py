from datetime import datetime
import os

class Logger:
    def __init__(self, log_file='app.log'):
        self.log_file = log_file
        self.ensure_log_file_exists()

    def ensure_log_file_exists(self):
        if not os.path.isfile(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("")

    def log(self, message):
        with open(self.log_file, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} - {message}\n")

    def log_error(self, error_message):
        self.log(f"ERROR: {error_message}")

    def log_info(self, info_message):
        self.log(f"INFO: {info_message}")