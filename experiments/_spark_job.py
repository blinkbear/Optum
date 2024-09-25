######################################## 
# This script is used for spark only!  #
# Do not directly execute this script! #
########################################
from pyspark.sql import SparkSession
import random

def calculate_pi(partitions):
    def inside(p):
        x, y = random.random(), random.random()
        return x * x + y * y < 1

    n = 100 * partitions

    spark = SparkSession.builder \
        .appName("PythonPi") \
        .getOrCreate()

    count = spark.sparkContext.parallelize(range(1, n + 1), partitions).filter(inside).count()
    pi = 4.0 * count / n
    print(f"Pi is roughly {pi}")

    spark.stop()

if __name__ == "__main__":
    partitions = 150000
    calculate_pi(partitions)
