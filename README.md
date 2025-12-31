# README: Writing your first hello-world Spark pipeline

This tutorial demonstrates writing your a Spark pipeline and pushing it to your ECR repo

**Note: You should be logged into the member account for the following steps**


## Prerequisites

This tutorial assumes the following:

1. You have given your Spark cluster access to S3 by using the steps defined in [Giving S3 access](/guides/giving-access-to-s3/).
2. You have IAM credentials setup for a user that's member of the `orchestera-platform-devs` and you have successfully verified your kubectl CLI permissions as documented [here](/guides/user-access-to-spark-cluster/).
3. You have cloned the repo at https://github.com/Orchestera/orchestera-hello-world.git
4. You have created a sample S3 bucket in your member account. Remember to plug in your bucket name in `<your-bucket-name>` in the code below.
5. You have created an ECR repo called `hello-world` in your member account and have noted the repo URI `<member-account-id>.dkr.ecr.us-east-1.amazonaws.com/hello-world`
6. Installed `uv` on your local machine. See this link: https://docs.astral.sh/uv/getting-started/installation/#installing-uv

From your local `orchestera-hello-world` directory, run the following:


```bash
make venv
source .venv/bin/activate
```

## Pipeline code

Update the `src/example/spark/application.py` with the following, replacing `<your-bucket-name>` with your actual S3 bucket.

```python
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

        bucket = "<your-bucket-name>"
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

```

## Building and Pushing the image to your ECR repo

Make sure to replace all instances of `member-account-id` with your actual account id that's part of your ECR URI

```bash
make build-userapp && make push-userapp ECR_REGISTRY=<member-account-id>.dkr.ecr.us-east-1.amazonaws.com
```


## Running the pipeline via Orchestera CLI

Now, you can run your pipeline using the following command:


```bash
uv run python -m orchestera.clients.sync_client run \
  --namespace "<your-namespace>" \
  --image "<member-account-id>.dkr.ecr.us-east-1.amazonaws.com/hello-world:userapp" \
  --classpath "example.spark.application.SparkK8sHelloWorld" \
  --application-name "spark-hello-world" --pull-secrets-from default

```

If you haven't setup secrets yet, you can remove `--pull-secrets-from default` from the args. Also make sure to specify the correct namespace.

Congratulations! You have created your first Spark pipeline application!

## Dev testing and building `orchestera-lib`

If testing orchestera-lib locally, add the following to your `pyproject.toml` file:

```
[tool.uv.sources]
orchestera-lib = { path = "../orchestera-lib", editable = true }

[dependency-groups]
dev = [
    "orchestera-lib",
]
```
