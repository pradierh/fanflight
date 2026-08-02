from hashlib import md5 as _md5
import pandas as pd

def process_flight(data, cursor, conn):
    rows = []
    
    for flight_type, is_best in [('best_flights', True), ('other_flights', False)]:
        for journey in data.get(flight_type, []):
            flights = journey.get('flights', [])
            layovers = journey.get('layovers', [])
            
            if not flights:
                continue
            
            journey_sk = _md5('_'.join([
                str([f['departure_airport']['id'] for f in flights]),
                str([f['arrival_airport']['id'] for f in flights]),
                str([f['airline'] for f in flights]),
                str([f['flight_number'] for f in flights]),
                flights[0]['departure_airport']['time'].split(' ')[0]
            ]).encode()).hexdigest()
            
            for pos, flight in enumerate(flights):
                flight_sk = _md5(
                    f"{journey_sk}_{flight['flight_number']}_{flight['departure_airport']['id']}_{pos}".encode()
                ).hexdigest()
                
                rows.append({
                    'journey_sk':              journey_sk,
                    'flight_sk':               flight_sk,
                    'departure_airport_code':  flight['departure_airport']['id'],
                    'departure_airport_time':  flight['departure_airport']['time'],
                    'arrival_airport_code':    flight['arrival_airport']['id'],
                    'arrival_airport_time':    flight['arrival_airport']['time'],
                    'duration':                flight.get('duration'),
                    'flight_number':           flight.get('flight_number'),
                    'layover_duration':        layovers[pos]['duration'] if pos < len(layovers) else None,
                    'total_journey_duration':  journey.get('total_duration'),
                    'price':                   journey.get('price'),
                    'airline':                 flight.get('airline'),
                    'airline_logo':            journey.get('airline_logo'),
                    'type':                    journey.get('type'),
                    'is_best':                 is_best,
                    'pos':                     pos
                })
    
    if not rows:
        return
    
    df = pd.DataFrame(rows).drop_duplicates(subset=['flight_sk'])
    
    # ← Enrichit les aéroports AVANT d'insérer dans FACT_FLIGHT
    _enrich_airports(df, cursor, conn)
    
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO fact_flight (
                flight_sk, journey_sk, departure_airport_code, departure_airport_time,
                arrival_airport_code, arrival_airport_time, duration, flight_number,
                layover_duration, total_journey_duration, price, airline, airline_logo,
                type, is_best, pos, updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
            ON CONFLICT (flight_sk) DO UPDATE SET
                price                  = EXCLUDED.price,
                departure_airport_time = EXCLUDED.departure_airport_time,
                updated_at             = CURRENT_TIMESTAMP
        """, (
            row['flight_sk'],
            row['journey_sk'],
            row['departure_airport_code'],
            row['departure_airport_time'],
            row['arrival_airport_code'],
            row['arrival_airport_time'],
            None if pd.isna(row['duration'])               else int(row['duration']),
            row['flight_number'],
            None if pd.isna(row['layover_duration'])        else int(row['layover_duration']),
            None if pd.isna(row['total_journey_duration'])  else int(row['total_journey_duration']),
            row['price'],
            row['airline'],
            row['airline_logo'],
            row['type'],
            row['is_best'],
            row['pos']
        ))
    
    conn.commit()


def _enrich_airports(df, cursor, conn):
    """Insère dans DIM_AIRPORT les codes IATA inconnus avant l'INSERT dans FACT_FLIGHT."""
    
    # Récupère tous les codes IATA du DataFrame
    iata_codes = set(df['departure_airport_code'].tolist() + df['arrival_airport_code'].tolist())
    
    # Filtre ceux déjà en base
    cursor.execute(
        "SELECT iata_code FROM DIM_AIRPORT WHERE iata_code = ANY(%s)",
        (list(iata_codes),)
    )
    known = {row['iata_code'] for row in cursor.fetchall()}
    unknown = iata_codes - known
    
    if not unknown:
        return
    
    # Charge le CSV de référence
    airports_csv = pd.read_csv('/opt/data/raw_data/airport-codes.csv')
    
    for iata in unknown:
        result = airports_csv[airports_csv['iata_code'].str.strip().str.upper() == iata.upper()]
        
        if not result.empty:
            row = result.iloc[0]
            city    = str(row.get('municipality', 'Unknown')).strip().title()
            country = str(row.get('iso_country',  'Unknown')).strip().upper()
            name    = str(row.get('name',          iata)).strip()
        else:
            city, country, name = 'Unknown', 'Unknown', iata
        
        # Insère la ville si inconnue
        cursor.execute("""
            INSERT INTO DIM_CITY (CITY, COUNTRY, IS_HOST_CITY)
            VALUES (%s, %s, FALSE)
            ON CONFLICT (CITY) DO NOTHING
        """, (city, country))
        
        cursor.execute(
            "SELECT ID_CITY FROM DIM_CITY WHERE LOWER(CITY) = LOWER(%s)",
            (city,)
        )
        id_city = cursor.fetchone()['id_city']
        
        # Insère l'aéroport
        cursor.execute("""
            INSERT INTO DIM_AIRPORT (IATA_CODE, NAME, ID_CITY)
            VALUES (%s, %s, %s)
            ON CONFLICT (IATA_CODE) DO NOTHING
        """, (iata, name, id_city))
    
    conn.commit()
    print(f"{len(unknown)} aéroports enrichis : {unknown}")