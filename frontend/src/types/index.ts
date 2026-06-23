export interface Airport {
  iata_code: string;
  name: string;
}

export interface City {
  id_city: string;
  city: string;
  country: string;
  flag: string
  airport_codes: string[];

}

export interface Team {
  team_name: string;
  team_code: string;
  flag: string;
}

export interface Match {
  match_id: number;          
  match_date: Date;        
  id_team_a: number;
  name_team_a: string;
  flag_team_a: string;
  id_team_b: number;
  name_team_b: string;
  flag_team_b: string;
  stage: string;             
  city_name: string;
}


export interface Segment {
  flight_sk: string;
  departure_airport_id: string;
  departure_airport_time: string;
  departure_city: string;
  arrival_airport_id: string;
  arrival_airport_time: string;
  arrival_city: string;
  duration: number | null;
  layover_duration: number | null;
  airline: string;
  pos: number;
}

export interface Flight {
  journey_sk: string;
  price: number;
  airline: string;
  is_best: boolean;
  total_duration: number | null;
  departure_airport_id: string;
  departure_airport_time: string;
  departure_city: string;
  arrival_airport_id: string;
  arrival_airport_time: string;
  arrival_city: string;
  nb_escales: number;
  segments: Segment[];
}


export type ViewState = 'city-select' | 'matches' | 'flights' | 'confirmation';


