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

flags = {
    'Afrique du Sud': ('RSA', '🇿🇦'),
    'Algérie': ('ALG', '🇩🇿'),
    'Allemagne': ('GER', '🇩🇪'),
    'Angleterre': ('ENG', '🏴󠁧󠁢󠁥󠁮󠁧󠁿'),
    'Arabie Saoudite': ('KSA', '🇸🇦'),
    'Argentine': ('ARG', '🇦🇷'),
    'Australie': ('AUS', '🇦🇺'),
    'Autriche': ('AUT', '🇦🇹'),
    'Belgique': ('BEL', '🇧🇪'),
    'Bosnie-Herzégovine': ('BIH', '🇧🇦'),
    'Brésil': ('BRA', '🇧🇷'),
    'Canada': ('CAN', '🇨🇦'),
    'Cap-Vert': ('CPV', '🇨🇻'),
    'Colombie': ('COL', '🇨🇴'),
    "Côte d'Ivoire": ('CIV', '🇨🇮'),
    'Croatie': ('CRO', '🇭🇷'),
    'Curaçao': ('CUW', '🇨🇼'),
    'Ecosse': ('SCO', '🏴󠁧󠁢󠁳󠁣󠁴󠁿'),
    'Égypte': ('EGY', '🇪🇬'),
    'Équateur': ('ECU', '🇪🇨'),
    'Espagne': ('ESP', '🇪🇸'),
    'États-Unis': ('USA', '🇺🇸'),
    'France': ('FRA', '🇫🇷'),
    'Ghana': ('GHA', '🇬🇭'),
    'Haïti': ('HAI', '🇭🇹'),
    'Irak': ('IRQ', '🇮🇶'),
    'Iran': ('IRN', '🇮🇷'),
    'Japon': ('JPN', '🇯🇵'),
    'Jordanie': ('JOR', '🇯🇴'),
    'Maroc': ('MAR', '🇲🇦'),
    'Mexique': ('MEX', '🇲🇽'),
    'Norvège': ('NOR', '🇳🇴'),
    'Nouvelle-Zélande': ('NZL', '🇳🇿'),
    'Ouzbékistan': ('UZB', '🇺🇿'),
    'Panama': ('PAN', '🇵🇦'),
    'Paraguay': ('PAR', '🇵🇾'),
    'Pays-Bas': ('NED', '🇳🇱'),
    'Portugal': ('POR', '🇵🇹'),
    'Qatar': ('QAT', '🇶🇦'),
    'RD Congo': ('COD', '🇨🇩'),
    'République de Corée': ('KOR', '🇰🇷'),
    'Sénégal': ('SEN', '🇸🇳'),
    'Suède': ('SWE', '🇸🇪'),
    'Suisse': ('SUI', '🇨🇭'),
    'Tchéquie': ('CZE', '🇨🇿'),
    'Tunisie': ('TUN', '🇹🇳'),
    'Turquie': ('TUR', '🇹🇷'),
    'Uruguay': ('URU', '🇺🇾'),
}

world_cup_data = {
    "New York": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("EWR", "Newark Liberty Intl"),
            ("JFK", "John F. Kennedy Intl"),
            ("LGA", "LaGuardia Airport")
        ],
        "matchs": [
            ["2026-06-13 18:00:00", "Brésil", "Maroc", "Phase de Groupe"],
            ["2026-06-16 15:00:00", "France", "Sénégal", "Phase de Groupe"],
            ["2026-06-22 20:00:00", "Norvège", "Sénégal", "Phase de Groupe"],
            ["2026-06-25 16:00:00", "Équateur", "Allemagne", "Phase de Groupe"],
            ["2026-06-27 17:00:00", "Panama", "Angleterre", "Phase de Groupe"]
        ]
    },
    "Los Angeles": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("LAX", "Los Angeles Intl"),
            ("BUR", "Hollywood Burbank"),
            ("SNA", "John Wayne Airport"),
            ("LGB", "Long Beach Airport")
        ],
        "matchs": [
            ["2026-06-12 21:00:00", "États-Unis", "Paraguay", "Phase de Groupe"],
            ["2026-06-15 21:00:00", "Iran", "Nouvelle-Zélande", "Phase de Groupe"],
            ["2026-06-18 15:00:00", "Suisse", "Bosnie-Herzégovine", "Phase de Groupe"],
            ["2026-06-21 15:00:00", "Belgique", "Iran", "Phase de Groupe"],
            ["2026-06-25 22:00:00", "Turquie", "États-Unis", "Phase de Groupe"]
        ]
    },
    "San Francisco": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("SFO", "San Francisco Intl"),
            ("SJC", "San Jose Mineta Intl"),
            ("OAK", "Oakland Intl")
        ],
        "matchs": [
            ["2026-06-13 15:00:00", "Qatar", "Suisse", "Phase de Groupe"],
            ["2026-06-16 00:00:00", "Autriche", "Jordanie", "Phase de Groupe"],
            ["2026-06-19 23:00:00", "Turquie", "Paraguay", "Phase de Groupe"],
            ["2026-06-22 23:00:00", "Jordanie", "Algérie", "Phase de Groupe"],
            ["2026-06-25 22:00:00", "Paraguay", "Australie", "Phase de Groupe"]
        ]
    },
    "Dallas": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("DFW", "Dallas/Fort Worth Intl"),
            ("DAL", "Dallas Love Field")
        ],
        "matchs": [
            ["2026-06-14 16:00:00", "Pays-Bas", "Japon", "Phase de Groupe"],
            ["2026-06-17 16:00:00", "Angleterre", "Croatie", "Phase de Groupe"],
            ["2026-06-22 13:00:00", "Argentine", "Autriche", "Phase de Groupe"],
            ["2026-06-25 19:00:00", "Japon", "Suède", "Phase de Groupe"],
            ["2026-06-27 22:00:00", "Jordanie", "Argentine", "Phase de Groupe"]
        ]
    },
    "Miami": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("MIA", "Miami Intl"),
            ("FLL", "Fort Lauderdale-Hollywood")
        ],
        "matchs": [
            ["2026-06-15 18:00:00", "Arabie Saoudite", "Uruguay", "Phase de Groupe"],
            ["2026-06-21 18:00:00", "Uruguay", "Cap-Vert", "Phase de Groupe"],
            ["2026-06-24 18:00:00", "Ecosse", "Brésil", "Phase de Groupe"],
            ["2026-06-27 19:30:00", "Colombie", "Portugal", "Phase de Groupe"]
        ]
    },
    "Houston": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("IAH", "George Bush Intercontinental"),
            ("HOU", "William P. Hobby Airport")
        ],
        "matchs": [
            ["2026-06-14 13:00:00", "Allemagne", "Curaçao", "Phase de Groupe"],
            ["2026-06-17 13:00:00", "Portugal", "RD Congo", "Phase de Groupe"],
            ["2026-06-20 13:00:00", "Pays-Bas", "Suède", "Phase de Groupe"],
            ["2026-06-23 13:00:00", "Portugal", "Ouzbékistan", "Phase de Groupe"],
            ["2026-06-26 20:00:00", "Cap-Vert", "Arabie Saoudite", "Phase de Groupe"]
        ]
    },
    "Atlanta": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("ATL", "Hartsfield-Jackson Atlanta")
        ],
        "matchs": [
            ["2026-06-15 12:00:00", "Espagne", "Cap-Vert", "Phase de Groupe"],
            ["2026-06-18 12:00:00", "Tchéquie", "Afrique du Sud", "Phase de Groupe"],
            ["2026-06-21 12:00:00", "Espagne", "Arabie Saoudite", "Phase de Groupe"],
            ["2026-06-24 18:00:00", "Maroc", "Haïti", "Phase de Groupe"],
            ["2026-06-27 19:30:00", "RD Congo", "Ouzbékistan", "Phase de Groupe"]
        ]
    },
    "Seattle": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("SEA", "Seattle-Tacoma Intl"),
            ("BFI", "Boeing Field")
        ],
        "matchs": [
            ["2026-06-15 15:00:00", "Belgique", "Égypte", "Phase de Groupe"],
            ["2026-06-19 15:00:00", "États-Unis", "Australie", "Phase de Groupe"],
            ["2026-06-24 15:00:00", "Bosnie-Herzégovine", "Qatar", "Phase de Groupe"],
            ["2026-06-26 23:00:00", "Égypte", "Iran", "Phase de Groupe"]
        ]
    },
    "Boston": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("BOS", "Boston Logan Intl")
        ],
        "matchs": [
            ["2026-06-13 21:00:00", "Haïti", "Ecosse", "Phase de Groupe"],
            ["2026-06-16 18:00:00", "Irak", "Norvège", "Phase de Groupe"],
            ["2026-06-19 18:00:00", "Ecosse", "Maroc", "Phase de Groupe"],
            ["2026-06-23 16:00:00", "Angleterre", "Ghana", "Phase de Groupe"],
            ["2026-06-26 15:00:00", "Norvège", "France", "Phase de Groupe"]
        ]
    },
    "Philadelphie": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("PHL", "Philadelphia Intl")
        ],
        "matchs": [
            ["2026-06-14 19:00:00", "Côte d'Ivoire", "Équateur", "Phase de Groupe"],
            ["2026-06-19 20:30:00", "Brésil", "Haïti", "Phase de Groupe"],
            ["2026-06-22 17:00:00", "France", "Irak", "Phase de Groupe"],
            ["2026-06-25 16:00:00", "Curaçao", "Côte d'Ivoire", "Phase de Groupe"],
            ["2026-06-27 17:00:00", "Croatie", "Ghana", "Phase de Groupe"]
        ]
    },
    "Kansas City": {
        "pays": "USA",
        "flag": '🇺🇸',
        "airports": [
            ("MCI", "Kansas City Intl")
        ],
        "matchs": [
            ["2026-06-16 21:00:00", "Argentine", "Algérie", "Phase de Groupe"],
            ["2026-06-20 20:00:00", "Équateur", "Curaçao", "Phase de Groupe"],
            ["2026-06-25 19:00:00", "Tunisie", "Pays-Bas", "Phase de Groupe"],
            ["2026-06-27 22:00:00", "Algérie", "Autriche", "Phase de Groupe"]
        ]
    },
    "Toronto": {
        "pays": "CAN",
        "flag": '🇨🇦',
        "airports": [
            ("YYZ", "Toronto Pearson Intl"),
            ("YTZ", "Billy Bishop Toronto City")
        ],
        "matchs": [
            ["2026-06-12 15:00:00", "Canada", "Bosnie-Herzégovine", "Phase de Groupe"],
            ["2026-06-17 19:00:00", "Ghana", "Panama", "Phase de Groupe"],
            ["2026-06-20 16:00:00", "Allemagne", "Côte d'Ivoire", "Phase de Groupe"],
            ["2026-06-23 19:00:00", "Panama", "Croatie", "Phase de Groupe"],
            ["2026-06-26 15:00:00", "Sénégal", "Irak", "Phase de Groupe"]
        ]
    },
    "Vancouver": {
        "pays": "CAN",
        "flag": '🇨🇦',
        "airports": [
            ("YVR", "Vancouver Intl")
        ],
        "matchs": [
            ["2026-06-13 00:00:00", "Australie", "Turquie", "Phase de Groupe"],
            ["2026-06-18 18:00:00", "Canada", "Qatar", "Phase de Groupe"],
            ["2026-06-21 21:00:00", "Nouvelle-Zélande", "Égypte", "Phase de Groupe"],
            ["2026-06-24 15:00:00", "Suisse", "Canada", "Phase de Groupe"],
            ["2026-06-26 23:00:00", "Nouvelle-Zélande", "Belgique", "Phase de Groupe"]
        ]
    },
    "Mexico City": {
        "pays": "MEX",
        "flag": '🇲🇽'
        "airports": [
            ("MEX", "Benito Juárez Intl"),
            ("NLU", "Felipe Ángeles Intl")
        ],
        "matchs": [
            ["2026-06-11 15:00:00", "Mexique", "Afrique du Sud", "Phase de Groupe"],
            ["2026-06-17 22:00:00", "Ouzbékistan", "Colombie", "Phase de Groupe"],
            ["2026-06-24 21:00:00", "Tchéquie", "Mexique", "Phase de Groupe"]
        ]
    },
    "Monterrey": {
        "pays": "MEX",
        "flag": '🇲🇽'
        "airports": [
            ("MTY", "Monterrey Intl")
        ],
        "matchs": [
            ["2026-06-14 22:00:00", "Suède", "Tunisie", "Phase de Groupe"],
            ["2026-06-20 00:00:00", "Tunisie", "Japon", "Phase de Groupe"],
            ["2026-06-24 21:00:00", "Afrique du Sud", "République de Corée", "Phase de Groupe"]
        ]
    },
    "Guadalajara": {
        "pays": "MEX",
        "flag": '🇲🇽'
        "airports": [
            ("GDL", "Miguel Hidalgo y Costilla Intl")
        ],
        "matchs": [
            ["2026-06-11 22:00:00", "République de Corée", "Tchéquie", "Phase de Groupe"],
            ["2026-06-18 21:00:00", "Mexique", "République de Corée", "Phase de Groupe"],
            ["2026-06-23 22:00:00", "Colombie", "RD Congo", "Phase de Groupe"],
            ["2026-06-26 20:00:00", "Uruguay", "Espagne", "Phase de Groupe"]
        ]
    }
}

for team_name, (code,flag) in flags.items():
    cursor.execute('''
                   INSERT INTO DIM_TEAM (TEAM_NAME, TEAM_CODE, FLAG_EMOJI)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (TEAM_NAME) DO NOTHING;
                   ''',
                   (team_name, code, flag)
                   )



for city, infos in world_cup_data.items():

    cursor.execute('''
                   INSERT INTO DIM_CITY (CITY, COUNTRY)
                   VALUES (%s, %s)
                   ON CONFLICT (CITY) DO NOTHING;
                   ''',
                   (city, infos['pays'])
                   )
    
for city, infos in world_cup_data.items():

    cursor.execute(
        "SELECT ID_CITY from DIM_CITY where CITY = %s",
        (city,)
        )

    id_city = cursor.fetchone()

    for iata, airport_name in infos['airports']:
        cursor.execute('''
                    INSERT INTO DIM_AIRPORT (IATA_CODE, NAME, ID_CITY) \
                    VALUES (%s, %s, %s)
                    ON CONFLICT (IATA_CODE) DO NOTHING;
                       ''',
                    (iata, airport_name, id_city)
                    )
    for matchs in infos['matchs']:

        cursor.execute("SELECT ID_TEAM FROM DIM_TEAM WHERE TEAM_NAME = %s", (matchs[1],))
        id_team_a= cursor.fetchone()[0]
        
        cursor.execute("SELECT ID_TEAM FROM DIM_TEAM WHERE TEAM_NAME = %s", (matchs[2],))
        id_team_b = cursor.fetchone()[0]

        cursor.execute('''
                    INSERT INTO FACT_MATCHS (MATCH_DATE, ID_TEAM_A, ID_TEAM_B, STAGE, ID_CITY)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT unique_match_per_location_time 
                    DO UPDATE SET ID_TEAM_A = EXCLUDED.ID_TEAM_A, ID_TEAM_B = EXCLUDED.ID_TEAM_B, STAGE = EXCLUDED.STAGE;
                    ''',
                    (matchs[0], id_team_a, id_team_b, matchs[3], id_city)
                    )
        

conn.commit()
cursor.close()
conn.close()