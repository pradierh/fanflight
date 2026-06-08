from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import ArrayType, StructType, StructField, IntegerType, StringType, BooleanType
import os
from stg_to_fact import stg_to_fact_flight
import sys

job_id = sys.argv[1]

spark = SparkSession.builder \
        .appName("Injestion vols") \
        .getOrCreate()

url = f"jdbc:postgresql://{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

properties = {
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "driver": "org.postgresql.Driver"
}


job_id = sys.argv[1]


df_raw = spark.read.jdbc(
    url=url,
    table=f"(SELECT json_data FROM flights_raw WHERE id = {job_id})",
    properties=properties
)

sample = df_raw.select("json_data").first()["json_data"]

schema = schema_of_json(sample)

df = df_raw.withColumn("parsed", from_json(col("json_data"), schema)).select(explode(col("parsed")).alias("response"))

#df = spark.read.option("multiLine",True).json("/opt/spark/data/raw_data/lot_reponses_api.json")

layover_schema = ArrayType(StructType([
    StructField("duration", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("id", StringType(), True),
    StructField("overnight", BooleanType(), True)
]))

df_best_flights = df.select(explode(col("response.best_flights")).alias("bf")) \
                    .withColumn("is_best", lit(True))


bf_cols = df_best_flights.select("bf.*").columns

layover_col = col("bf.layovers") if "layovers" in bf_cols else lit(None).cast(layover_schema)

df_best_flights = df_best_flights.withColumn("journey_sk",
                                               md5(concat_ws('_',
                                                             col("bf.flights.departure_airport.id"),
                                                             col("bf.flights.arrival_airport.id"),
                                                             col("bf.flights.airline"),
                                                             col("bf.flights.flight_number"),
                                                             to_date(col("bf.flights")[0]["departure_airport"]["time"])))) #on prend la date sans l'heure pour l'unicité du voyage si jamais ça chnage d'heure de depart, la sk ne chnage pas 

df_detail_best_flight = df_best_flights.select(
                                          "journey_sk",
                                          posexplode("bf.flights").alias("pos", "flight"),
                                          layover_col.alias("layovers"),
                                          col("bf.total_duration").alias("total_journey_duration"),
                                          "bf.price",
                                          "bf.airline_logo",
                                          "bf.type",
                                          "is_best")


df_detail_best_flight = df_detail_best_flight.withColumn("flight_sk",
                                                   md5(concat_ws('_',
                                                       col("journey_sk"),
                                                       col("flight.flight_number"),
                                                       col("flight.departure_airport.id"),
                                                       col("pos")
                                                       )))


df_detail_best_flight = df_detail_best_flight.select(
                        "journey_sk",
                        col("flight.departure_airport.id").alias("departure_airport_id"),
                        col("flight.departure_airport.time").cast("timestamp").alias("departure_airport_time"),
                        col("flight.arrival_airport.id").alias("arrival_airport_id"),
                        col("flight.arrival_airport.time").cast("timestamp").alias("arrival_airport_time"),
                        col("flight.duration").alias("duration"),
                        get(col("layovers"),col("pos")).getField("duration").alias("layover_duration"),
                        "total_journey_duration",
                        "price",
                        "flight.airline",
                        "airline_logo",
                        "type",
                        "flight_sk",
                        "is_best",
                        "pos")



df_other_flights = df.select(explode(col("response.other_flights")).alias("of")) \
                    .withColumn("is_best", lit(False))


of_cols = df_other_flights.select("of.*").columns

layover_col = col("of.layovers") if "layovers" in of_cols else lit(None).cast(layover_schema)

df_other_flights = df_other_flights.withColumn("journey_sk",
                                               md5(concat_ws('_',
                                                             col("of.flights.departure_airport.id"),
                                                             col("of.flights.arrival_airport.id"),
                                                             col("of.flights.airline"),
                                                             col("of.flights.flight_number"),
                                                             to_date(col("of.flights")[0]["departure_airport"]["time"]))))

df_detail_other_flight = df_other_flights.select("journey_sk",
                                          posexplode("of.flights").alias("pos", "flight"),
                                          layover_col.alias("layovers"),
                                          col("of.total_duration").alias("total_journey_duration"),
                                          "of.price",
                                          "of.airline_logo",
                                          "of.type",
                                          "is_best")



df_detail_other_flight = df_detail_other_flight.withColumn("flight_sk",
                                                   md5(concat_ws('_',
                                                       col("journey_sk"),
                                                       col("flight.flight_number"),
                                                       col("flight.departure_airport.id"),
                                                       col("pos")
                                                       )))


df_detail_other_flight = df_detail_other_flight.select(
                        "journey_sk",
                        col("flight.departure_airport.id").alias("departure_airport_id"),
                        col("flight.departure_airport.time").cast("timestamp").alias("departure_airport_time"),
                        col("flight.arrival_airport.id").alias("arrival_airport_id"),
                        col("flight.arrival_airport.time").cast("timestamp").alias("arrival_airport_time"), #change le type en timestamp pour injestion en bd
                        col("flight.duration").alias("duration"),
                        get(col("layovers"),col("pos")).getField("duration").alias("layover_duration"),
                        "total_journey_duration",
                        "price",
                        "flight.airline",
                        "airline_logo",
                        "type",
                        "flight_sk",
                        "is_best",
                        "pos")

df_detail_best_flight.show()
df_detail_other_flight.show()


df_final_to_load = df_detail_best_flight.unionByName(df_detail_other_flight)


try:
    df_final_to_load.write.jdbc(
        url=url,
        table="STG_FLIGHT",
        mode="overwrite",
        properties=properties
    )
    print("Transfert vers Postgres réussi !")
except Exception as e:
    print(f"Erreur lors du transfert : {e}")


stg_to_fact_flight(job_id)

