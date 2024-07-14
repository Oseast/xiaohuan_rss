import logging
import os

class LoggerConfig:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self, name='my_app_logger', log_file='app.log', level=logging.DEBUG):
        if not hasattr(self, 'initialized'):  # 防止重复初始化
            self.initialized = True

            # 设置日志文件的路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            log_file_path = os.path.join(base_dir, 'log', log_file)
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

            # 创建logger
            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)

            # 避免重复添加处理器
            if not self.logger.handlers:
                # 创建FileHandler，指定文件编码为UTF-8
                file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
                file_handler.setLevel(level)

                # 创建并设置formatter
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(formatter)

                # 添加handler到logger
                self.logger.addHandler(file_handler)

                # 可选：添加控制台处理器，方便调试
                console_handler = logging.StreamHandler()
                console_handler.setLevel(level)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger


