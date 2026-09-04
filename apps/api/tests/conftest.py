"""Keep the automated suite deterministic and independent of paid providers."""

import os

os.environ["APP_ENV"] = "test"
os.environ["XFYUN_MAAS_API_KEY"] = ""
os.environ["XFYUN_SPARK_API_PASSWORD"] = ""
os.environ["XFYUN_SPARK_API_KEY"] = ""
os.environ["XFYUN_SPARK_API_SECRET"] = ""
