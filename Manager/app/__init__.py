import logging

# yzh1019: centralized logging setup for manager service.
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
