from datetime import datetime
import logging
import os
import sys
import uuid
import pytz

# 全局变量，用于存储程序启动后的日志文件名和日志实例池
_global_log_filename = None
_logger_pool = {}

# 自定义格式化器，支持时区和相对路径
class CustomFormatter(logging.Formatter):
    """自定义格式化器，支持时区和相对路径"""
    def __init__(self, fmt=None, datefmt=None, tz=None):
        super().__init__(fmt, datefmt)
        # 如果tz是字符串，则转换为tzinfo对象
        if isinstance(tz, str):
            try:
                self.tz = pytz.timezone(tz)
            except:
                self.tz = None
        else:
            self.tz = tz
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def converter(self, timestamp):
        if self.tz:
            dt = datetime.fromtimestamp(timestamp, tz=self.tz)
            return dt.timetuple()
        return datetime.fromtimestamp(timestamp).timetuple()
        
    def formatMessage(self, record):
        # 获取完整路径
        pathname = record.pathname
        # 转换为相对路径
        if pathname.startswith(self.project_root):
            record.filename = os.path.relpath(pathname, self.project_root)
        else:
            # 如果不是项目根目录下的文件，尝试获取更完整的路径
            # 获取文件名和行号
            filename = record.filename
            # 尝试从pathname中提取更完整的路径
            if pathname:
                # 从pathname中提取最后几级目录
                parts = pathname.split(os.sep)
                if len(parts) >= 3:
                    # 使用最后三级目录作为相对路径
                    record.filename = os.path.join(parts[-3], parts[-2], parts[-1])
                elif len(parts) >= 2:
                    # 使用最后两级目录作为相对路径
                    record.filename = os.path.join(parts[-2], parts[-1])
        
        # 清理消息中的特殊字符，避免编码问题
        if isinstance(record.msg, str):
            # 移除零宽空格和其他不可打印字符
            record.msg = ''.join(c for c in record.msg if c.isprintable() and ord(c) < 65536)
        
        return super().formatMessage(record)

def create_logger(log_filename, timezone='Asia/Shanghai', level=logging.DEBUG, console_output=True, handlers=None):
    """创建日志实例
    
    Args:
        log_filename: 日志文件名
        timezone: 时区
        level: 日志级别
        console_output: 是否输出到控制台
        handlers: 自定义处理器列表
        
    Returns:
        logging.Logger: 日志实例
    """
    # 创建唯一的logger名称
    logger_name = f"Logger_{uuid.uuid4()}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.handlers = []  # 清除已有的handlers
    
    # 创建格式化器
    log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    formatter = CustomFormatter(log_format, tz=timezone)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 如果提供了自定义处理器，添加它们
    if handlers:
        for handler in handlers:
            logger.addHandler(handler)
    # 否则，如果需要控制台输出，添加控制台处理器
    elif console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    logger.propagate = False
    
    return logger

def set_global_log_filename(log_filename):
    """设置全局日志文件名
    
    Args:
        log_filename: 日志文件名
    """
    global _global_log_filename
    _global_log_filename = log_filename

def setup_logger(log_filename_prefix=None, level='DEBUG', log_dir="logs", console_output=True, naive=False):
    """设置日志
    
    Args:
        log_filename_prefix: 日志文件名前缀
        level: 日志级别
        log_dir: 日志目录
        console_output: 是否输出到控制台
        naive: 是否使用naive的日志设置. 如果为True, 则使用logging.basicConfig设置日志, 否则使用create_logger设置日志.
    Returns:
        logging.Logger: 日志实例
    """
    import logging
    if naive:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        return logger

    global _global_log_filename, _logger_pool
    
    # 转换日志级别
    level_map = {'INFO': logging.INFO, 'DEBUG': logging.DEBUG, "WARN": logging.WARN}
    log_level = level_map.get(level, logging.DEBUG)
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 如果全局日志文件名已经设置，则使用它
    if _global_log_filename:
        log_filename = _global_log_filename
    else:
        # 生成日志文件名
        time_str = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        if not log_filename_prefix:
            log_filename = f"{log_dir}/{time_str}.log"
        else:
            log_filename = f"{log_dir}/{log_filename_prefix}_{time_str}.log"
        
        # 设置全局日志文件名
        _global_log_filename = log_filename
    
    # 如果日志实例已经存在，则直接返回
    if log_filename in _logger_pool:
        return _logger_pool[log_filename]
    
    # 创建日志实例
    logger = create_logger(log_filename, "Asia/Shanghai", log_level, console_output)
    
    # 保存到日志实例池
    _logger_pool[log_filename] = logger
    
    return logger
