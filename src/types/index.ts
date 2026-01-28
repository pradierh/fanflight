export interface City {
  id: string;
  name: string;
  country: 'USA' | 'Mexico' | 'Canada';
  stadium: string;
  airportCode: string;
  coordinates: {
    lat: number;
    lng: number;
  };
}

export interface Team {
  id: string;
  name: string;
  code: string;
  flag: string;
}

export interface Match {
  id: string;
  homeTeam: Team;
  awayTeam: Team;
  city: City;
  date: Date;
  group: string;
  stage: 'group' | 'round16' | 'quarter' | 'semi' | 'final';
}

export type FlightRiskStatus = 'on-time' | 'potential-delay' | 'high-risk';

export interface FlightRiskFactors {
  weather: 'clear' | 'cloudy' | 'rain' | 'storm';
  historicalOnTime: number; // percentage
  distance: number; // miles
}

export interface Flight {
  id: string;
  airline: string;
  flightNumber: string;
  origin: City;
  destination: City;
  departureTime: Date;
  arrivalTime: Date;
  price: number;
  seatsAvailable: number;
  riskStatus: FlightRiskStatus;
  riskFactors: FlightRiskFactors;
}

export interface BookingWindow {
  opensAt: Date;
  closesAt: Date;
  isOpen: boolean;
  timeRemaining: number; // milliseconds
}

export type ViewState = 'city-select' | 'matches' | 'flights' | 'confirmation';

export interface BookingState {
  originCity: City | null;
  selectedMatch: Match | null;
  selectedFlight: Flight | null;
  view: ViewState;
}
