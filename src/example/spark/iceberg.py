"""
Module for a sample PySpark application demonstrating Iceberg with S3.
"""
import logging

from orchestera.spark.session import OrchesteraSparkSession
from orchestera.entrypoints.sparklith_entrypoint import SparklithEntryPoint
from orchestera.entrypoints.base_entrypoint import StringArg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IcebergS3Example(SparklithEntryPoint):

    application_name = StringArg(required=True, tooltip="Name of the application")

    def run(self):
        """Code entrypoint for Iceberg S3 example"""

        bucket = "sparklith-warehouse-feb13"
        warehouse_path = f"s3a://{bucket}/iceberg-warehouse"

        # Iceberg runtime packages (compatible with Spark 3.5)
        # See: https://iceberg.apache.org/releases/
        iceberg_version = "1.10.1"
        iceberg_packages = ",".join([
            f"org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:{iceberg_version}",
            f"org.apache.iceberg:iceberg-aws-bundle:{iceberg_version}",
        ])

        # Iceberg-specific Spark configuration
        iceberg_conf = {
            # Include Iceberg JARs at runtime
            "spark.jars.packages": iceberg_packages,
            # Catalog configuration
            "spark.sql.catalog.spark_catalog": "org.apache.iceberg.spark.SparkSessionCatalog",
            "spark.sql.catalog.spark_catalog.type": "hive",
            "spark.sql.catalog.local": "org.apache.iceberg.spark.SparkCatalog",
            "spark.sql.catalog.local.type": "hadoop",
            "spark.sql.catalog.local.warehouse": warehouse_path,
            "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        }

        with OrchesteraSparkSession(
            app_name="IcebergS3Example",
            executor_instances=4,
            executor_cores=2,
            executor_memory="8g",
            additional_spark_conf=iceberg_conf,
        ) as spark:
            spark.sparkContext.setLogLevel("ERROR")

            # Read sample data from publicly available S3
            df = spark.read.parquet(
                "s3a://ookla-open-data/parquet/performance/type=fixed/year=2019/quarter=1/2019-01-01_performance_fixed_tiles.parquet"
            ).limit(1000)

            logger.info("Sample data schema:")
            df.printSchema()
            df.show(5)

            # Create Iceberg table and write data
            table_name = "local.example.ookla_performance"

            # Create namespace if it doesn't exist
            spark.sql("CREATE NAMESPACE IF NOT EXISTS local.example")

            # Write DataFrame as Iceberg table
            df.writeTo(table_name).createOrReplace()
            logger.info(f"Created Iceberg table: {table_name}")

            # Read back from Iceberg table
            iceberg_df = spark.table(table_name)
            logger.info("Reading from Iceberg table:")
            iceberg_df.show(5)

            # Demonstrate Iceberg SQL features
            # Append more data
            df.writeTo(table_name).append()
            logger.info("Appended data to Iceberg table")

            # Show table history (time travel metadata)
            spark.sql(f"SELECT * FROM {table_name}.history").show()

            # Show table snapshots
            spark.sql(f"SELECT * FROM {table_name}.snapshots").show()

            logger.info("Iceberg S3 example completed successfully")
