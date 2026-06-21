import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

cursor = conn.cursor()

# Coordonnées lat/lon ajoutées pour l'enrichissement météo Open-Meteo.
# Format : (IATA, nom, latitude, longitude)

world_cup_data = {
    "New York": {
        "pays": "USA",
        "airports": [
            ("EWR", "Newark Liberty Intl",        40.6895, -74.1745),
            ("JFK", "John F. Kennedy Intl",        40.6413, -73.7781),
            ("LGA", "LaGuardia Airport",           40.7769, -73.8740),
        ],
        "matchs": [
            ["2026-06-13 18:00:00", "Brésil",    "Maroc",      "Phase de Groupe"],
            ["2026-06-16 15:00:00", "France",    "Sénégal",    "Phase de Groupe"],
            ["2026-06-22 20:00:00", "Norvège",   "Sénégal",    "Phase de Groupe"],
            ["2026-06-25 16:00:00", "Équateur",  "Allemagne",  "Phase de Groupe"],
            ["2026-06-27 17:00:00", "Panamá",    "Angleterre", "Phase de Groupe"],
        ],
    },
    "Los Angeles": {
        "pays": "USA",
        "airports": [
            ("LAX", "Los Angeles Intl",       33.9425, -118.4081),
            ("BUR", "Hollywood Burbank",       34.2007, -118.3585),
            ("SNA", "John Wayne Airport",      33.6757, -117.8682),
            ("LGB", "Long Beach Airport",      33.8177, -118.1516),
        ],
        "matchs": [
            ["2026-06-12 21:00:00", "États-Unis",  "Paraguay",             "Phase de Groupe"],
            ["2026-06-15 21:00:00", "RI Iran",     "Nouvelle-Zélande",     "Phase de Groupe"],
            ["2026-06-18 15:00:00", "Suisse",      "Bosnie-et-Herzégovine","Phase de Groupe"],
            ["2026-06-21 15:00:00", "Belgique",    "RI Iran",              "Phase de Groupe"],
            ["2026-06-25 22:00:00", "Turquie",     "États-Unis",           "Phase de Groupe"],
        ],
    },
    "San Francisco": {
        "pays": "USA",
        "airports": [
            ("SFO", "San Francisco Intl",    37.6213, -122.3790),
            ("SJC", "San Jose Mineta Intl",  37.3626, -121.9290),
            ("OAK", "Oakland Intl",          37.7213, -122.2208),
        ],
        "matchs": [
            ["2026-06-13 15:00:00", "Qatar",    "Suisse",    "Phase de Groupe"],
            ["2026-06-16 00:00:00", "Autriche", "Jordanie",  "Phase de Groupe"],
            ["2026-06-19 23:00:00", "Turquie",  "Paraguay",  "Phase de Groupe"],
            ["2026-06-22 23:00:00", "Jordanie", "Algérie",   "Phase de Groupe"],
            ["2026-06-25 22:00:00", "Paraguay", "Australie", "Phase de Groupe"],
        ],
    },
    "Dallas": {
        "pays": "USA",
        "airports": [
            ("DFW", "Dallas/Fort Worth Intl", 32.8998, -97.0403),
            ("DAL", "Dallas Love Field",      32.8481, -96.8512),
        ],
        "matchs": [
            ["2026-06-14 16:00:00", "Pays-Bas",  "Japon",     "Phase de Groupe"],
            ["2026-06-17 16:00:00", "Angleterre","Croatie",   "Phase de Groupe"],
            ["2026-06-22 13:00:00", "Argentine", "Autriche",  "Phase de Groupe"],
            ["2026-06-25 19:00:00", "Japon",     "Suède",     "Phase de Groupe"],
            ["2026-06-27 22:00:00", "Jordanie",  "Argentine", "Phase de Groupe"],
        ],
    },
    "Miami": {
        "pays": "USA",
        "airports": [
            ("MIA", "Miami Intl",                  25.7959, -80.2870),
            ("FLL", "Fort Lauderdale-Hollywood",   26.0726, -80.1527),
        ],
        "matchs": [
            ["2026-06-15 18:00:00", "Arabie Saoudite", "Uruguay",  "Phase de Groupe"],
            ["2026-06-21 18:00:00", "Uruguay",         "Cap-Vert", "Phase de Groupe"],
            ["2026-06-24 18:00:00", "Écosse",          "Brésil",   "Phase de Groupe"],
            ["2026-06-27 19:30:00", "Colombie",        "Portugal", "Phase de Groupe"],
        ],
    },
    "Houston": {
        "pays": "USA",
        "airports": [
            ("IAH", "George Bush Intercontinental", 29.9902, -95.3368),
            ("HOU", "William P. Hobby Airport",     29.6454, -95.2789),
        ],
        "matchs": [
            ["2026-06-14 13:00:00", "Allemagne", "Curaçao",     "Phase de Groupe"],
            ["2026-06-17 13:00:00", "Portugal",  "RD Congo",    "Phase de Groupe"],
            ["2026-06-20 13:00:00", "Pays-Bas",  "Suède",       "Phase de Groupe"],
            ["2026-06-23 13:00:00", "Portugal",  "Ouzbékistan", "Phase de Groupe"],
            ["2026-06-26 20:00:00", "Cap-Vert",  "Arabie Saoudite","Phase de Groupe"],
        ],
    },
    "Atlanta": {
        "pays": "USA",
        "airports": [
            ("ATL", "Hartsfield-Jackson Atlanta", 33.6407, -84.4277),
        ],
        "matchs": [
            ["2026-06-15 12:00:00", "Espagne",  "Cap-Vert",       "Phase de Groupe"],
            ["2026-06-18 12:00:00", "Tchéquie", "Afrique du Sud", "Phase de Groupe"],
            ["2026-06-21 12:00:00", "Espagne",  "Arabie Saoudite","Phase de Groupe"],
            ["2026-06-24 18:00:00", "Maroc",    "Haïti",          "Phase de Groupe"],
            ["2026-06-27 19:30:00", "RD Congo", "Ouzbékistan",    "Phase de Groupe"],
        ],
    },
    "Seattle": {
        "pays": "USA",
        "airports": [
            ("SEA", "Seattle-Tacoma Intl", 47.4502, -122.3088),
            ("BFI", "Boeing Field",        47.5300, -122.3019),
        ],
        "matchs": [
            ["2026-06-15 15:00:00", "Belgique",            "Égypte",   "Phase de Groupe"],
            ["2026-06-19 15:00:00", "États-Unis",          "Australie","Phase de Groupe"],
            ["2026-06-24 15:00:00", "Bosnie-et-Herzégovine","Qatar",   "Phase de Groupe"],
            ["2026-06-26 23:00:00", "Égypte",              "RI Iran",  "Phase de Groupe"],
        ],
    },
    "Boston": {
        "pays": "USA",
        "airports": [
            ("BOS", "Boston Logan Intl", 42.3656, -71.0096),
        ],
        "matchs": [
            ["2026-06-13 21:00:00", "Haïti",    "Écosse",  "Phase de Groupe"],
            ["2026-06-16 18:00:00", "Irak",     "Norvège", "Phase de Groupe"],
            ["2026-06-19 18:00:00", "Écosse",   "Maroc",   "Phase de Groupe"],
            ["2026-06-23 16:00:00", "Angleterre","Ghana",  "Phase de Groupe"],
            ["2026-06-26 15:00:00", "Norvège",  "France",  "Phase de Groupe"],
        ],
    },
    "Philadelphie": {
        "pays": "USA",
        "airports": [
            ("PHL", "Philadelphia Intl", 39.8744, -75.2424),
        ],
        "matchs": [
            ["2026-06-14 19:00:00", "Côte d'Ivoire","Équateur",      "Phase de Groupe"],
            ["2026-06-19 20:30:00", "Brésil",       "Haïti",         "Phase de Groupe"],
            ["2026-06-22 17:00:00", "France",        "Irak",          "Phase de Groupe"],
            ["2026-06-25 16:00:00", "Curaçao",       "Côte d'Ivoire", "Phase de Groupe"],
            ["2026-06-27 17:00:00", "Croatie",       "Ghana",         "Phase de Groupe"],
        ],
    },
    "Kansas City": {
        "pays": "USA",
        "airports": [
            ("MCI", "Kansas City Intl", 39.2976, -94.7139),
        ],
        "matchs": [
            ["2026-06-16 21:00:00", "Argentine", "Algérie",   "Phase de Groupe"],
            ["2026-06-20 20:00:00", "Équateur",  "Curaçao",   "Phase de Groupe"],
            ["2026-06-25 19:00:00", "Tunisie",   "Pays-Bas",  "Phase de Groupe"],
            ["2026-06-27 22:00:00", "Algérie",   "Autriche",  "Phase de Groupe"],
        ],
    },
    "Toronto": {
        "pays": "Canada",
        "airports": [
            ("YYZ", "Toronto Pearson Intl",       43.6777, -79.6248),
            ("YTZ", "Billy Bishop Toronto City",  43.6275, -79.3962),
        ],
        "matchs": [
            ["2026-06-12 15:00:00", "Canada",    "Bosnie-et-Herzégovine","Phase de Groupe"],
            ["2026-06-17 19:00:00", "Ghana",     "Panamá",               "Phase de Groupe"],
            ["2026-06-20 16:00:00", "Allemagne", "Côte d'Ivoire",        "Phase de Groupe"],
            ["2026-06-23 19:00:00", "Panamá",    "Croatie",              "Phase de Groupe"],
            ["2026-06-26 15:00:00", "Sénégal",   "Irak",                 "Phase de Groupe"],
        ],
    },
    "Vancouver": {
        "pays": "Canada",
        "airports": [
            ("YVR", "Vancouver Intl", 49.1967, -123.1815),
        ],
        "matchs": [
            ["2026-06-13 00:00:00", "Australie",      "Turquie",   "Phase de Groupe"],
            ["2026-06-18 18:00:00", "Canada",          "Qatar",     "Phase de Groupe"],
            ["2026-06-21 21:00:00", "Nouvelle-Zélande","Égypte",   "Phase de Groupe"],
            ["2026-06-24 15:00:00", "Suisse",          "Canada",    "Phase de Groupe"],
            ["2026-06-26 23:00:00", "Nouvelle-Zélande","Belgique", "Phase de Groupe"],
        ],
    },
    "Mexico City": {
        "pays": "Mexique",
        "airports": [
            ("MEX", "Benito Juárez Intl",   19.4363,  -99.0721),
            ("NLU", "Felipe Ángeles Intl",  19.7460,  -99.0151),
        ],
        "matchs": [
            ["2026-06-11 15:00:00", "Mexique",     "Afrique du Sud", "Phase de Groupe"],
            ["2026-06-17 22:00:00", "Ouzbékistan", "Colombie",       "Phase de Groupe"],
            ["2026-06-24 21:00:00", "Tchéquie",    "Mexique",        "Phase de Groupe"],
        ],
    },
    "Monterrey": {
        "pays": "Mexique",
        "airports": [
            ("MTY", "Monterrey Intl", 25.7785, -100.1067),
        ],
        "matchs": [
            ["2026-06-14 22:00:00", "Suède",        "Tunisie",              "Phase de Groupe"],
            ["2026-06-20 00:00:00", "Tunisie",       "Japon",               "Phase de Groupe"],
            ["2026-06-24 21:00:00", "Afrique du Sud","République de Corée", "Phase de Groupe"],
        ],
    },
    "Guadalajara": {
        "pays": "Mexique",
        "airports": [
            ("GDL", "Miguel Hidalgo y Costilla Intl", 20.5218, -103.3110),
        ],
        "matchs": [
            ["2026-06-11 22:00:00", "République de Corée","Tchéquie",  "Phase de Groupe"],
            ["2026-06-18 21:00:00", "Mexique",             "République de Corée","Phase de Groupe"],
            ["2026-06-23 22:00:00", "Colombie",            "RD Congo",  "Phase de Groupe"],
            ["2026-06-26 20:00:00", "Uruguay",             "Espagne",   "Phase de Groupe"],
        ],
    },
}

# ------------------------------------------------------------------
# INSERT
# ------------------------------------------------------------------

for city, infos in world_cup_data.items():
    cursor.execute(
        "INSERT INTO DIM_CITY (CITY, COUNTRY) VALUES (%s, %s) ON CONFLICT (CITY) DO NOTHING;",
        (city, infos["pays"]),
    )

for city, infos in world_cup_data.items():
    cursor.execute("SELECT ID_CITY FROM DIM_CITY WHERE CITY = %s", (city,))
    id_city = cursor.fetchone()[0]

    for airport in infos["airports"]:
        iata, name, lat, lon = airport
        cursor.execute(
            """
            INSERT INTO DIM_AIRPORT (IATA_CODE, NAME, ID_CITY, LATITUDE, LONGITUDE)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (IATA_CODE) DO UPDATE
                SET LATITUDE  = EXCLUDED.LATITUDE,
                    LONGITUDE = EXCLUDED.LONGITUDE;
            """,
            (iata, name, id_city, lat, lon),
        )

    for match in infos["matchs"]:
        cursor.execute(
            """
            INSERT INTO FACT_MATCHS (MATCH_DATE, TEAM_A, TEAM_B, STAGE, ID_CITY)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT unique_match_per_location_time
            DO UPDATE SET TEAM_A = EXCLUDED.TEAM_A,
                          TEAM_B = EXCLUDED.TEAM_B,
                          STAGE  = EXCLUDED.STAGE;
            """,
            (match[0], match[1], match[2], match[3], id_city),
        )

conn.commit()
cursor.close()
conn.close()

print("load_static_data OK — villes, aéroports (avec coordonnées) et matchs insérés.")
