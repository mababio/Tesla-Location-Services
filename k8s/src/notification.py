from retry import retry
# from logs import logger
import sys
import redis
sys.path.append('../')


def publish(message):

    if not isinstance(message, (bytes, str, float, int)):
        message = str(message)
    r = redis.Redis(
        host='redis-pub-sub',
        port=6379,
        decode_responses=True
    )
    r.publish('chanify-notification', message)


# @retry(logger=logger, delay=2, tries=2)
def send_push_notification(message):
    publish(message)


if __name__ == "__main__":
    send_push_notification('testing')
