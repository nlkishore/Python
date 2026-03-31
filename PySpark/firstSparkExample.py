import pyspark
from pyspark.sql import SparkSession
import os

#JAVA_HOME = "C:/Program Files/Java/jdk-11"
JAVA_HOME = "C:/Program Files/Java/jdk1.8.0_202"
os.environ["PATH"] = f"{JAVA_HOME}/bin:{os.environ['PATH']}"  # Note /bin is added to JAVA_HOME path.

#from pyspark.sql import SparkSession
#spark=SparkSession.builder.appName('Practise').getOrCreate()

columns = ["language","users_count"]
data = [("Java", "20000"), ("Python", "100000"), ("Scala", "3000")]
spark = (
     SparkSession.builder.master("local") # type: ignore
         .appName("Word Count")
         .config("spark.some.config.option", "some-value")
         .getOrCreate()
 )
rdd = spark.sparkContext.parallelize(data)
# Create DataFrame
df = spark.createDataFrame(
    [("Scala", 25000), ("Spark", 35000), ("PHP", 21000)])
df.show()