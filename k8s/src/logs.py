import logging
import os
import redis
from io import StringIO


class Logger:
    def __init__(self, name, level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        logger_format = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(message)s"
        self.log_stream = StringIO()
        logging.basicConfig(stream=self.log_stream, format=logger_format)
        self.logger.setLevel(level)
        console_output_handler = logging.StreamHandler()
        console_output_handler.setFormatter(logging.Formatter(logger_format))
        self.logger.addHandler(console_output_handler)
        try:
            self.redis_host = os.environ['REDIS_HOST']
            self.redis_channel = os.environ['REDIS_CHANIFY_CHANNEL']
            self.r = redis.Redis(
                host=self.redis_host,
                port=6379,
                decode_responses=True
            )
        except KeyError:
            print('REDIS_HOST or REDIS_CHANIFY_CHANNEL not env variables  not set')
            self.logger.info('REDIS_HOST or REDIS_CHANIFY_CHANNEL not env variables  not set')
            self.r = None

        try:
            if self.r is not None:
                self.r.ping()
                self.logger.info('Redis connection successful')
                self.r.publish(self.redis_channel, self.log_stream.getvalue())
        except redis.exceptions.ConnectionError:
            print('Redis connection error')
            self.logger.critical('Redis connection error')
            self.r = None

    def info(self, message):
        self.logger.info(message)
        if self.r and self.logger.level == logging.DEBUG:
            self.r.publish(self.redis_channel, self.log_stream.getvalue())

    def error(self, message):
        self.logger.error(message)
        if self.r:
            self.r.publish(self.redis_channel, self.log_stream.getvalue())

    def debug(self, message):
        self.logger.debug(message)
        if self.r:
            self.r.publish(self.redis_channel, self.log_stream.getvalue())

    def warning(self, message):
        self.logger.warning(message)
        if self.r and self.logger.level == logging.DEBUG:
            self.r.publish(self.redis_channel, self.log_stream.getvalue())


if __name__ == "__main__":
    # os.environ['REDIS_HOST'] = 'localhost'
    # os.environ['REDIS_CHANIFY_CHANNEL'] = 'chanify-notification'
    LOG = Logger('test', logging.WARNING)
    LOG.warning('test')
    LOG.error('test2')
