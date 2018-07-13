import logging


tornado_gen_logger = logging.getLogger("tornado.general")
tornado_gen_logger.setLevel(logging.ERROR)

urllib_logger = logging.getLogger("urllib3")
urllib_logger.setLevel(logging.INFO)

elasticsearch_logger = logging.getLogger("elasticsearch")
elasticsearch_logger.setLevel(logging.INFO)
