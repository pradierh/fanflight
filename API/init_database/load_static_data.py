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

# ------------------------------------------------------------------
# ÉQUIPES — nom, code FIFA, drapeau emoji
# ------------------------------------------------------------------

flags = {
    'Afrique du Sud':      ('RSA', '🇿🇦'),
    'Algérie':             ('ALG', '🇩🇿'),
    'Allemagne':           ('GER', '🇩🇪'),
    'Angleterre':          ('ENG', '🏴󠁧󠁢󠁥󠁮󠁧󠁿'),
    'Arabie Saoudite':     ('KSA', '🇸🇦'),
    'Argentine':           ('ARG', '🇦🇷'),
    'Australie':           ('AUS', '🇦🇺'),
    'Autriche':            ('AUT', '🇦🇹'),
    'Belgique':            ('BEL', '🇧🇪'),
    'Bosnie-Herzégovine':  ('BIH', '🇧🇦'),
    'Brésil':              ('BRA', '🇧🇷'),
    'Canada':              ('CAN', '🇨🇦'),
    'Cap-Vert':            ('CPV', '🇨🇻'),
    'Colombie':            ('COL', '🇨🇴'),
    "Côte d'Ivoire":       ('CIV', '🇨🇮'),
    'Croatie':             ('CRO', '🇭🇷'),
    'Curaçao':             ('CUW', '🇨🇼'),
    'Ecosse':              ('SCO', '🏴󠁧󠁢󠁳󠁣󠁴󠁿'),
    'Égypte':              ('EGY', '🇪🇬'),
    'Équateur':            ('ECU', '🇪🇨'),
    'Espagne':             ('ESP', '🇪🇸'),
    'États-Unis':          ('USA', '🇺🇸'),
    'France':              ('FRA', '🇫🇷'),
    'Ghana':               ('GHA', '🇬🇭'),
    'Haïti':               ('HAI', '🇭🇹'),
    'Irak':                ('IRQ', '🇮🇶'),
    'Iran':                ('IRN', '🇮🇷'),
    'Japon':               ('JPN', '🇯🇵'),
    'Jordanie':            ('JOR', '🇯🇴'),
    'Maroc':               ('MAR', '🇲🇦'),
    'Mexique':             ('MEX', '🇲🇽'),
    'Norvège':             ('NOR', '🇳🇴'),
    'Nouvelle-Zélande':    ('NZL', '🇳🇿'),
    'Ouzbékistan':         ('UZB', '🇺🇿'),
    'Panama':              ('PAN', '🇵🇦'),
    'Paraguay':            ('PAR', '🇵🇾'),
    'Pays-Bas':            ('NED', '🇳🇱'),
    'Portugal':            ('POR', '🇵🇹'),
    'Qatar':               ('QAT', '🇶🇦'),
    'RD Congo':            ('COD', '🇨🇩'),
    'République de Corée': ('KOR', '🇰🇷'),
    'Sénégal':             ('SEN', '🇸🇳'),
    'Suède':               ('SWE', '🇸🇪'),
    'Suisse':              ('SUI', '🇨🇭'),
    'Tchéquie':            ('CZE', '🇨🇿'),
    'Tunisie':             ('TUN', '🇹🇳'),
    'Turquie':             ('TUR', '🇹🇷'),
    'Uruguay':             ('URU', '🇺🇾'),
}

# ------------------------------------------------------------------
# DONNÉES COUPE DU MONDE 2026
# Aéroports : (IATA, nom, latitude, longitude)
# ------------------------------------------------------------------

world_cup_data = {
    "New York": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("EWR", "Newark Liberty Intl",  40.6895, -74.1745),
            ("JFK", "John F. Kennedy Intl", 40.6413, -73.7781),
            ("LGA", "LaGuardia Airport",    40.7769, -73.8740),
        ],
        "matchs": [
            ["2026-08-13 18:00:00", "Brésil",   "Maroc",      "Phase de Groupe"],
            ["2026-08-16 15:00:00", "France",   "Sénégal",    "Phase de Groupe"],
            ["2026-08-22 20:00:00", "Norvège",  "Sénégal",    "Phase de Groupe"],
            ["2026-08-25 16:00:00", "Équateur", "Allemagne",  "Phase de Groupe"],
            ["2026-08-27 17:00:00", "Panama",   "Angleterre", "Phase de Groupe"],
        ],
    },
    "Los Angeles": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("LAX", "Los Angeles Intl",    33.9425, -118.4081),
            ("BUR", "Hollywood Burbank",   34.2007, -118.3585),
            ("SNA", "John Wayne Airport",  33.6757, -117.8682),
            ("LGB", "Long Beach Airport",  33.8177, -118.1516),
        ],
        "matchs": [
            ["2026-08-12 21:00:00", "États-Unis",       "Paraguay",          "Phase de Groupe"],
            ["2026-08-15 21:00:00", "Iran",              "Nouvelle-Zélande",  "Phase de Groupe"],
            ["2026-08-18 15:00:00", "Suisse",            "Bosnie-Herzégovine","Phase de Groupe"],
            ["2026-08-21 15:00:00", "Belgique",          "Iran",              "Phase de Groupe"],
            ["2026-08-25 22:00:00", "Turquie",           "États-Unis",        "Phase de Groupe"],
        ],
    },
    "San Francisco": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("SFO", "San Francisco Intl",   37.6213, -122.3790),
            ("SJC", "San Jose Mineta Intl", 37.3626, -121.9290),
            ("OAK", "Oakland Intl",         37.7213, -122.2208),
        ],
        "matchs": [
            ["2026-08-13 15:00:00", "Qatar",    "Suisse",    "Phase de Groupe"],
            ["2026-08-16 00:00:00", "Autriche", "Jordanie",  "Phase de Groupe"],
            ["2026-08-19 23:00:00", "Turquie",  "Paraguay",  "Phase de Groupe"],
            ["2026-08-22 23:00:00", "Jordanie", "Algérie",   "Phase de Groupe"],
            ["2026-08-25 22:00:00", "Paraguay", "Australie", "Phase de Groupe"],
        ],
    },
    "Dallas": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("DFW", "Dallas/Fort Worth Intl", 32.8998, -97.0403),
            ("DAL", "Dallas Love Field",      32.8481, -96.8512),
        ],
        "matchs": [
            ["2026-08-14 16:00:00", "Pays-Bas",  "Japon",     "Phase de Groupe"],
            ["2026-08-17 16:00:00", "Angleterre","Croatie",   "Phase de Groupe"],
            ["2026-08-22 13:00:00", "Argentine", "Autriche",  "Phase de Groupe"],
            ["2026-08-25 19:00:00", "Japon",     "Suède",     "Phase de Groupe"],
            ["2026-08-27 22:00:00", "Jordanie",  "Argentine", "Phase de Groupe"],
        ],
    },
    "Miami": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("MIA", "Miami Intl",                25.7959, -80.2870),
            ("FLL", "Fort Lauderdale-Hollywood", 26.0726, -80.1527),
        ],
        "matchs": [
            ["2026-08-15 18:00:00", "Arabie Saoudite", "Uruguay",  "Phase de Groupe"],
            ["2026-08-21 18:00:00", "Uruguay",         "Cap-Vert", "Phase de Groupe"],
            ["2026-08-24 18:00:00", "Ecosse",          "Brésil",   "Phase de Groupe"],
            ["2026-08-27 19:30:00", "Colombie",        "Portugal", "Phase de Groupe"],
        ],
    },
    "Houston": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("IAH", "George Bush Intercontinental", 29.9902, -95.3368),
            ("HOU", "William P. Hobby Airport",     29.6454, -95.2789),
        ],
        "matchs": [
            ["2026-08-14 13:00:00", "Allemagne", "Curaçao",       "Phase de Groupe"],
            ["2026-08-17 13:00:00", "Portugal",  "RD Congo",      "Phase de Groupe"],
            ["2026-08-20 13:00:00", "Pays-Bas",  "Suède",         "Phase de Groupe"],
            ["2026-08-23 13:00:00", "Portugal",  "Ouzbékistan",   "Phase de Groupe"],
            ["2026-08-26 20:00:00", "Cap-Vert",  "Arabie Saoudite","Phase de Groupe"],
        ],
    },
    "Atlanta": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("ATL", "Hartsfield-Jackson Atlanta", 33.6407, -84.4277),
        ],
        "matchs": [
            ["2026-08-15 12:00:00", "Espagne",  "Cap-Vert",        "Phase de Groupe"],
            ["2026-08-18 12:00:00", "Tchéquie", "Afrique du Sud",  "Phase de Groupe"],
            ["2026-08-21 12:00:00", "Espagne",  "Arabie Saoudite", "Phase de Groupe"],
            ["2026-08-24 18:00:00", "Maroc",    "Haïti",           "Phase de Groupe"],
            ["2026-08-27 19:30:00", "RD Congo", "Ouzbékistan",     "Phase de Groupe"],
        ],
    },
    "Seattle": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("SEA", "Seattle-Tacoma Intl", 47.4502, -122.3088),
            ("BFI", "Boeing Field",        47.5300, -122.3019),
        ],
        "matchs": [
            ["2026-08-15 15:00:00", "Belgique",        "Égypte",    "Phase de Groupe"],
            ["2026-08-19 15:00:00", "États-Unis",      "Australie", "Phase de Groupe"],
            ["2026-08-24 15:00:00", "Bosnie-Herzégovine","Qatar",   "Phase de Groupe"],
            ["2026-08-26 23:00:00", "Égypte",          "Iran",      "Phase de Groupe"],
        ],
    },
    "Boston": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("BOS", "Boston Logan Intl", 42.3656, -71.0096),
        ],
        "matchs": [
            ["2026-08-13 21:00:00", "Haïti",    "Ecosse",  "Phase de Groupe"],
            ["2026-08-16 18:00:00", "Irak",     "Norvège", "Phase de Groupe"],
            ["2026-08-19 18:00:00", "Ecosse",   "Maroc",   "Phase de Groupe"],
            ["2026-08-23 16:00:00", "Angleterre","Ghana",  "Phase de Groupe"],
            ["2026-08-26 15:00:00", "Norvège",  "France",  "Phase de Groupe"],
        ],
    },
    "Philadelphie": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("PHL", "Philadelphia Intl", 39.8744, -75.2424),
        ],
        "matchs": [
            ["2026-08-14 19:00:00", "Côte d'Ivoire","Équateur",       "Phase de Groupe"],
            ["2026-08-19 20:30:00", "Brésil",       "Haïti",          "Phase de Groupe"],
            ["2026-08-22 17:00:00", "France",        "Irak",           "Phase de Groupe"],
            ["2026-08-25 16:00:00", "Curaçao",       "Côte d'Ivoire",  "Phase de Groupe"],
            ["2026-08-27 17:00:00", "Croatie",       "Ghana",          "Phase de Groupe"],
        ],
    },
    "Kansas City": {
        "pays": "US",
        "flag": '🇺🇸',
        "airports": [
            ("MCI", "Kansas City Intl", 39.2976, -94.7139),
        ],
        "matchs": [
            ["2026-08-16 21:00:00", "Argentine", "Algérie",  "Phase de Groupe"],
            ["2026-08-20 20:00:00", "Équateur",  "Curaçao",  "Phase de Groupe"],
            ["2026-08-25 19:00:00", "Tunisie",   "Pays-Bas", "Phase de Groupe"],
            ["2026-08-27 22:00:00", "Algérie",   "Autriche", "Phase de Groupe"],
        ],
    },
    "Toronto": {
        "pays": "CA",
        "flag": '🇨🇦',
        "airports": [
            ("YYZ", "Toronto Pearson Intl",      43.6777, -79.6248),
            ("YTZ", "Billy Bishop Toronto City", 43.6275, -79.3962),
        ],
        "matchs": [
            ["2026-08-12 15:00:00", "Canada",    "Bosnie-Herzégovine","Phase de Groupe"],
            ["2026-08-17 19:00:00", "Ghana",     "Panama",            "Phase de Groupe"],
            ["2026-08-20 16:00:00", "Allemagne", "Côte d'Ivoire",     "Phase de Groupe"],
            ["2026-08-23 19:00:00", "Panama",    "Croatie",           "Phase de Groupe"],
            ["2026-08-26 15:00:00", "Sénégal",   "Irak",              "Phase de Groupe"],
        ],
    },
    "Vancouver": {
        "pays": "CA",
        "flag": '🇨🇦',
        "airports": [
            ("YVR", "Vancouver Intl", 49.1967, -123.1815),
        ],
        "matchs": [
            ["2026-08-13 00:00:00", "Australie",      "Turquie",          "Phase de Groupe"],
            ["2026-08-18 18:00:00", "Canada",          "Qatar",            "Phase de Groupe"],
            ["2026-08-21 21:00:00", "Nouvelle-Zélande","Égypte",           "Phase de Groupe"],
            ["2026-08-24 15:00:00", "Suisse",          "Canada",           "Phase de Groupe"],
            ["2026-08-26 23:00:00", "Nouvelle-Zélande","Belgique",         "Phase de Groupe"],
        ],
    },
    "Mexico City": {
        "pays": "MX",
        "flag": '🇲🇽',
        "airports": [
            ("MEX", "Benito Juárez Intl",  19.4363, -99.0721),
            ("NLU", "Felipe Ángeles Intl", 19.7460, -99.0151),
        ],
        "matchs": [
            ["2026-08-11 15:00:00", "Mexique",     "Afrique du Sud", "Phase de Groupe"],
            ["2026-08-17 22:00:00", "Ouzbékistan", "Colombie",       "Phase de Groupe"],
            ["2026-08-24 21:00:00", "Tchéquie",    "Mexique",        "Phase de Groupe"],
        ],
    },
    "Monterrey": {
        "pays": "MX",
        "flag": '🇲🇽',
        "airports": [
            ("MTY", "Monterrey Intl", 25.7785, -100.1067),
        ],
        "matchs": [
            ["2026-08-14 22:00:00", "Suède",         "Tunisie",             "Phase de Groupe"],
            ["2026-08-20 00:00:00", "Tunisie",        "Japon",              "Phase de Groupe"],
            ["2026-08-24 21:00:00", "Afrique du Sud", "République de Corée","Phase de Groupe"],
        ],
    },
    "Guadalajara": {
        "pays": "MX",
        "flag": '🇲🇽',
        "airports": [
            ("GDL", "Miguel Hidalgo y Costilla Intl", 20.5218, -103.3110),
        ],
        "matchs": [
            ["2026-08-11 22:00:00", "République de Corée","Tchéquie",           "Phase de Groupe"],
            ["2026-08-18 21:00:00", "Mexique",             "République de Corée","Phase de Groupe"],
            ["2026-08-23 22:00:00", "Colombie",            "RD Congo",           "Phase de Groupe"],
            ["2026-08-26 20:00:00", "Uruguay",             "Espagne",            "Phase de Groupe"],
        ],
    },
}

# ------------------------------------------------------------------
# INSERTS
# ------------------------------------------------------------------

# DIM_TEAM
for team_name, (code, flag) in flags.items():
    cursor.execute("""
        INSERT INTO DIM_TEAM (TEAM_NAME, TEAM_CODE, FLAG)
        VALUES (%s, %s, %s)
        ON CONFLICT (TEAM_NAME) DO NOTHING;
    """, (team_name, code, flag))

# DIM_CITY
for city, infos in world_cup_data.items():
    cursor.execute("""
        INSERT INTO DIM_CITY (CITY, COUNTRY, FLAG, IS_HOST_CITY)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (CITY) DO UPDATE
            SET FLAG         = EXCLUDED.FLAG,
                IS_HOST_CITY = EXCLUDED.IS_HOST_CITY;
    """, (city, infos['pays'], infos['flag']))

# DIM_AIRPORT + FACT_MATCHS
for city, infos in world_cup_data.items():
    cursor.execute("SELECT ID_CITY FROM DIM_CITY WHERE CITY = %s", (city,))
    id_city = cursor.fetchone()[0]

    # Aéroports — avec coordonnées lat/lon pour l'inférence météo
    for iata, name, lat, lon in infos['airports']:
        cursor.execute("""
            INSERT INTO DIM_AIRPORT (IATA_CODE, NAME, ID_CITY, LATITUDE, LONGITUDE)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (IATA_CODE) DO NOTHING;
        """, (iata, name, id_city, lat, lon))

    # Matchs — avec FK vers DIM_TEAM
    for match in infos['matchs']:
        cursor.execute("SELECT ID_TEAM FROM DIM_TEAM WHERE TEAM_NAME = %s", (match[1],))
        id_team_a = cursor.fetchone()[0]

        cursor.execute("SELECT ID_TEAM FROM DIM_TEAM WHERE TEAM_NAME = %s", (match[2],))
        id_team_b = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO FACT_MATCHS (MATCH_DATE, ID_TEAM_A, ID_TEAM_B, STAGE, ID_CITY)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT unique_match_per_location_time
            DO UPDATE SET ID_TEAM_A = EXCLUDED.ID_TEAM_A,
                          ID_TEAM_B = EXCLUDED.ID_TEAM_B,
                          STAGE     = EXCLUDED.STAGE;
        """, (match[0], id_team_a, id_team_b, match[3], id_city))

conn.commit()
cursor.close()
conn.close()

print("load_static_data OK — équipes, villes, aéroports (avec coordonnées) et matchs insérés.")