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


EXECUTOR_IMAGE = "853027285987.dkr.ecr.us-east-1.amazonaws.com/hello-world:latest"


class SparkK8sHelloWorld(SparklithEntryPoint):

    application_name = StringArg(required=True, tooltip="Name of the application")
    # image = StringArg(required=True, tooltip="Image to use for the application")

    def run(self):
        """Code entrypoint"""

        additional_spark_conf = {
            "spark.default.parallelism": 4,

            # Override executor image
            "spark.kubernetes.executor.container.image": EXECUTOR_IMAGE,

            # Explicitly add the JARs to executor classpath
            "spark.executor.extraClassPath": "/opt/spark/jars/hadoop-aws-3.3.4.jar:/opt/spark/jars/aws-java-sdk-bundle-1.12.746.jar",


            # Allow EKS Pod Identity agent FULL_URI host for AWS SDK v1
            "spark.driver.extraJavaOptions": "-Dcom.amazonaws.sdk.ecsFullUriAllowedHosts=169.254.170.23,localhost,127.0.0.1",
            "spark.executor.extraJavaOptions": "-Dcom.amazonaws.sdk.ecsFullUriAllowedHosts=169.254.170.23,localhost,127.0.0.1",

            # Service account for pod identity
            "spark.kubernetes.authenticate.driver.serviceAccountName": "spark",
            "spark.kubernetes.authenticate.executor.serviceAccountName": "spark",

            # Hadoop AWS filesystem
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",

            # Use EKS Pod Identity container credentials
            "spark.hadoop.fs.s3a.aws.credentials.provider": (
                "com.amazonaws.auth.EC2ContainerCredentialsProviderWrapper"
            ),

            # Prevent IMDS from being used as a fallback so node instance profile doesn't override Pod Identity
            "spark.executorEnv.AWS_EC2_METADATA_DISABLED": "true",
            "spark.kubernetes.driverEnv.AWS_EC2_METADATA_DISABLED": "true",

            # Optional: faster committers for Spark
            "spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version": "2",
            "spark.hadoop.fs.s3a.committer.name": "directory",
            "spark.hadoop.fs.s3a.committer.magic.enabled": "false",

            # Set HOME to writable directory for executors
            "spark.executorEnv.HOME": "/tmp",
            "spark.executorEnv.PYSPARK_PYTHON": "python3",
        }

        with OrchesteraSparkSession(
            app_name="SparkK8sHelloWorld",
            executor_instances=4,
            executor_cores=1,
            executor_memory="2g",
            additional_spark_conf=additional_spark_conf,
        ) as spark:
            # Ensure default parallelism equals number of executors
            try:
                num_executors = int(spark.sparkContext.getConf().get("spark.executor.instances", "1"))
            except ValueError:
                num_executors = 1

            bucket = "sparklith-warehouse-sep29"
            prefix = "spark-outputs/"

            # Always process only the provided base CSV files
            base_files = [
                "wc-product-export-women.csv",
                "wc-product-export-men.csv",
            ]

            # Prepare the input keys for only the specified base CSVs
            input_keys = [f"{prefix}{name}" for name in base_files]

            # Read each CSV with Spark and write back with the '-new.csv' suffix
            for key in input_keys:
                input_uri = f"s3a://{bucket}/{key}"
                base_name = os.path.basename(key)[:-4]  # strip .csv
                output_uri = f"s3a://{bucket}/{prefix}{base_name}-new.csv"

                logger.info("Processing %s -> %s", input_uri, output_uri)
                df = spark.read.option("header", True).csv(input_uri)

                # Use number of executors for parallelism
                num_partitions = num_executors if num_executors > 0 else 1
                if num_partitions > 1:
                    df = df.repartition(num_partitions)

                # Overwrite output using Spark (folder semantics on S3)
                df.coalesce(1).write.mode("overwrite").option("header", True).csv(output_uri)
