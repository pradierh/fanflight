from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import (
    ArrayType, StructType, StructField,
    IntegerType, StringType, BooleanType
)
import os
import sys
from stg_to_fact import stg_to_fact_flight

job_id = sys.argv[1]

spark = SparkSession.builder \
    .appName("Ingestion vols") \
    .getOrCreate()

url = f"jdbc:postgresql://{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

properties = {
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "driver": "org.postgresql.Driver"
}

# ------------------------------------------------------------------
# Lecture du JSON brut (cast en text pour from_json)
# Alias "AS t" requis par Spark pour les sous-requêtes JDBC.
# ------------------------------------------------------------------
df_raw = spark.read.jdbc(
    url=url,
    table=f"(SELECT json_data::text AS json_data FROM flights_raw WHERE id = {job_id}) AS t",
    properties=properties
)

# ------------------------------------------------------------------
# Schéma EXPLICITE — évite que schema_of_json supprime "layovers"
# quand l'échantillon n'en contient pas.
# Inclut "often_delayed_by_over_30_min" = label de retard (Google Flights).
# ------------------------------------------------------------------
airport_schema = StructType([
    StructField("id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("time", StringType(), True),
])

layover_schema = StructType([
    StructField("id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("duration", IntegerType(), True),
    StructField("overnight", BooleanType(), True),
])

flight_leg_schema = StructType([
    StructField("departure_airport", airport_schema, True),
    StructField("arrival_airport", airport_schema, True),
    StructField("duration", IntegerType(), True),
    StructField("airline", StringType(), True),
    StructField("airline_logo", StringType(), True),
    StructField("flight_number", StringType(), True),
    StructField("travel_class", StringType(), True),
    StructField("airplane", StringType(), True),
    StructField("legroom", StringType(), True),
    StructField("often_delayed_by_over_30_min", BooleanType(), True),
])

journey_schema = StructType([
    StructField("flights", ArrayType(flight_leg_schema), True),
    StructField("layovers", ArrayType(layover_schema), True),
    StructField("total_duration", IntegerType(), True),
    StructField("price", IntegerType(), True),
    StructField("type", StringType(), True),
    StructField("airline_logo", StringType(), True),
])

response_schema = StructType([
    StructField("best_flights", ArrayType(journey_schema), True),
    StructField("other_flights", ArrayType(journey_schema), True),
])

outer_schema = ArrayType(response_schema)

# Parsing
df = df_raw.withColumn("parsed", from_json(col("json_data"), outer_schema)) \
           .select(explode(col("parsed")).alias("response"))

# ==================================================================
# BEST FLIGHTS
# ==================================================================
df_best_flights = df.select(explode(col("response.best_flights")).alias("bf")) \
                    .withColumn("is_best", lit(True))

df_best_flights = df_best_flights.withColumn(
    "journey_sk",
    md5(concat_ws('_',
        col("bf.flights.departure_airport.id"),
        col("bf.flights.arrival_airport.id"),
        col("bf.flights.airline"),
        col("bf.flights.flight_number"),
        to_date(col("bf.flights")[0]["departure_airport"]["time"])
    ))
)

df_detail_best_flight = df_best_flights.select(
    "journey_sk",
    posexplode("bf.flights").alias("pos", "flight"),
    col("bf.layovers").alias("layovers"),
    col("bf.total_duration").alias("total_journey_duration"),
    "bf.price",
    "bf.airline_logo",
    "bf.type",
    "is_best"
)

df_detail_best_flight = df_detail_best_flight.withColumn(
    "flight_sk",
    md5(concat_ws('_',
        col("journey_sk"),
        col("flight.flight_number"),
        col("flight.departure_airport.id"),
        col("pos")
    ))
)

df_detail_best_flight = df_detail_best_flight.select(
    "journey_sk",
    col("flight.departure_airport.id").alias("departure_airport_id"),
    col("flight.departure_airport.time").cast("timestamp").alias("departure_airport_time"),
    col("flight.arrival_airport.id").alias("arrival_airport_id"),
    col("flight.arrival_airport.time").cast("timestamp").alias("arrival_airport_time"),
    col("flight.duration").alias("duration"),
    get(col("layovers"), col("pos")).getField("duration").alias("layover_duration"),
    "total_journey_duration",
    "price",
    "flight.airline",
    "airline_logo",
    "type",
    "flight_sk",
    "is_best",
    "pos",
    col("flight.often_delayed_by_over_30_min").cast("boolean").alias("is_delayed"),
)

# ==================================================================
# OTHER FLIGHTS
# ==================================================================
df_other_flights = df.select(explode(col("response.other_flights")).alias("of")) \
                    .withColumn("is_best", lit(False))

df_other_flights = df_other_flights.withColumn(
    "journey_sk",
    md5(concat_ws('_',
        col("of.flights.departure_airport.id"),
        col("of.flights.arrival_airport.id"),
        col("of.flights.airline"),
        col("of.flights.flight_number"),
        to_date(col("of.flights")[0]["departure_airport"]["time"])
    ))
)

df_detail_other_flight = df_other_flights.select(
    "journey_sk",
    posexplode("of.flights").alias("pos", "flight"),
    col("of.layovers").alias("layovers"),
    col("of.total_duration").alias("total_journey_duration"),
    "of.price",
    "of.airline_logo",
    "of.type",
    "is_best"
)

df_detail_other_flight = df_detail_other_flight.withColumn(
    "flight_sk",
    md5(concat_ws('_',
        col("journey_sk"),
        col("flight.flight_number"),
        col("flight.departure_airport.id"),
        col("pos")
    ))
)

df_detail_other_flight = df_detail_other_flight.select(
    "journey_sk",
    col("flight.departure_airport.id").alias("departure_airport_id"),
    col("flight.departure_airport.time").cast("timestamp").alias("departure_airport_time"),
    col("flight.arrival_airport.id").alias("arrival_airport_id"),
    col("flight.arrival_airport.time").cast("timestamp").alias("arrival_airport_time"),
    col("flight.duration").alias("duration"),
    get(col("layovers"), col("pos")).getField("duration").alias("layover_duration"),
    "total_journey_duration",
    "price",
    "flight.airline",
    "airline_logo",
    "type",
    "flight_sk",
    "is_best",
    "pos",
    col("flight.often_delayed_by_over_30_min").cast("boolean").alias("is_delayed"),
)

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
