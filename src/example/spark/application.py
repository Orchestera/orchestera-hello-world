"""
Module for a sample PySpark application with the driver running in client mode.
"""
import os
import logging

from pyspark.sql.functions import length
from orchestera.spark.session import OrchesteraSparkSession

from orchestera.entrypoints.sparklith_entrypoint import SparklithEntryPoint

from orchestera.entrypoints.base_entrypoint import StringArg  # type: ignore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EXECUTOR_IMAGE = "ghcr.io/orchestera/docker-images/spark:latest"


class SparkK8sHelloWorld(SparklithEntryPoint):

    application_name = StringArg(required=True, tooltip="Name of the application")

    def run(self):
        """Code entrypoint"""

        with OrchesteraSparkSession(
            app_name="SparkK8sHelloWorld",
            executor_instances=4,
            executor_cores=1,
            executor_memory="2g",
            additional_spark_conf={},
        ) as spark:

            bucket = "sparklith-warehouse-sep29"
            prefix = "spark-outputs/"

            # Always process only the provided base CSV files
            base_files = [
                "wc-product-export-women.csv",
                "wc-product-export-men.csv",
            ]

            # Prepare the input keys for only the specified base CSVs
            input_keys = [f"{prefix}{name}" for name in base_files]

            logger.info("Testing envar retrieval for DATABASE_URL: %s", os.environ.get("DATABASE_URL"))

            # Read each CSV with Spark and write back with the '-new.csv' suffix
            for key in input_keys:
                input_uri = f"s3a://{bucket}/{key}"
                base_name = os.path.basename(key)[:-4]  # strip .csv
                output_uri = f"s3a://{bucket}/{prefix}{base_name}-new.csv"

                logger.info("Processing %s -> %s", input_uri, output_uri)
                df = spark.read.option("header", True).csv(input_uri)

                # Use number of executors for parallelism
                df = df.repartition(4)

                # Overwrite output using Spark (folder semantics on S3)
                df.coalesce(1).write.mode("overwrite").option("header", True).csv(output_uri)
