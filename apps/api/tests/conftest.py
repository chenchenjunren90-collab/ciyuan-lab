"""Keep the automated suite deterministic and independent of paid providers."""

import os

os.environ["APP_ENV"] = "test"
os.environ["XFYUN_MAAS_API_KEY"] = ""
os.environ["XFYUN_SPARK_API_PASSWORD"] = ""
os.environ["XFYUN_SPARK_API_KEY"] = ""
os.environ["XFYUN_SPARK_API_SECRET"] = ""
# Pin the provider route and clear the DeepSeek key so a developer-local .env
# can never leak real credentials or routes into the offline test suite.
os.environ["MODEL_PROVIDER"] = "xfyun_maas"
os.environ["DEEPSEEK_API_KEY"] = ""
