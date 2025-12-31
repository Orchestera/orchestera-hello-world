"""
Module for a sample PySpark application with the driver running in client mode.
"""
import os
import logging

from pyspark.sql import SparkSession

from orchestera.spark.session import OrchesteraSparkSession

from orchestera.entrypoints.sparklith_entrypoint import SparklithEntryPoint

from orchestera.entrypoints.base_entrypoint import StringArg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SparkK8sHelloWorld(SparklithEntryPoint):

    application_name = StringArg(required=True, tooltip="Name of the application")

    def run(self):
        """Code entrypoint"""

        bucket = "sparklith-warehouse-sep29"
        prefix = "ookla-outputs"

        with OrchesteraSparkSession(
            app_name="SparkK8sHelloWorld",
            executor_instances=4,
            executor_cores=2,
            executor_memory="8g",
            additional_spark_conf={},
        ) as spark:
            logger.info("Testing envar retrieval for DATABASE_URL: %s", os.environ.get("DATABASE_URL"))
            
            sqlContext = SparkSession(spark)
            spark.sparkContext.setLogLevel("ERROR")

            # Read OOKLA metrics from publicly available S3 data
            df = spark.read.parquet("s3a://ookla-open-data/parquet/performance/type=fixed/year=2019/quarter=1/2019-01-01_performance_fixed_tiles.parquet").repartition(4)
            
            df.show()
            print(df.printSchema())

            df.createOrReplaceTempView('tempSource')

            print('Register the DataFrame as a SQL temporary view: source')
            df.createOrReplaceTempView('tempSource')
            
            newdf = spark.sql('SELECT * FROM tempSource LIMIT 1000')

            # Write CSV
            output_uri_csv = f"s3a://{bucket}/{prefix}/newdf.csv"
            newdf.write.mode("overwrite").option("header", True).csv(output_uri_csv)

            # Write Parquet
            output_uri_parquet = f"s3a://{bucket}/{prefix}/newdfparquet"
            newdf.write.mode("overwrite").option("compression", "snappy").parquet(output_uri_parquet)
