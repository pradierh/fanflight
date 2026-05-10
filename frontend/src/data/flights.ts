import { Flight, FlightRiskStatus, City } from '@/types';

const AIRLINES = [
  'United Airlines',
  'American Airlines',
  'Delta Air Lines',
  'Southwest Airlines',
  'JetBlue Airways',
  'Alaska Airlines',
  'Aeromexico',
  'Air Canada'
];

// Calculate distance between two coordinates (haversine formula)
const calculateDistance = (city1: City, city2: City): number => {
  const R = 3959; // Earth's radius in miles
  const dLat = (city2.coordinates.lat - city1.coordinates.lat) * Math.PI / 180;
  const dLon = (city2.coordinates.lng - city1.coordinates.lng) * Math.PI / 180;
  const a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(city1.coordinates.lat * Math.PI / 180) * Math.cos(city2.coordinates.lat * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return Math.round(R * c);
};

// Generate flight risk based on probability
const generateRiskStatus = (): FlightRiskStatus => {
  const rand = Math.random();
  if (rand < 0.70) return 'on-time';
  if (rand < 0.90) return 'potential-delay';
  return 'high-risk';
};

// Generate weather condition
const generateWeather = (): 'clear' | 'cloudy' | 'rain' | 'storm' => {
  const rand = Math.random();
  if (rand < 0.5) return 'clear';
  if (rand < 0.75) return 'cloudy';
  if (rand < 0.92) return 'rain';
  return 'storm';
};

// Generate random flight number
const generateFlightNumber = (airline: string): string => {
  const prefix = airline.split(' ')[0].substring(0, 2).toUpperCase();
  const number = Math.floor(Math.random() * 9000) + 1000;
  return `${prefix}${number}`;
};

// Generate price based on distance and demand
const generatePrice = (distance: number, daysUntilMatch: number): number => {
  const basePrice = 150;
  const distanceFactor = distance * 0.15;
  const demandFactor = daysUntilMatch <= 1 ? 1.5 : daysUntilMatch <= 2 ? 1.2 : 1;
  const randomFactor = 0.8 + Math.random() * 0.4;
  return Math.round((basePrice + distanceFactor) * demandFactor * randomFactor);
};

// Generate flight duration based on distance
const generateDuration = (distance: number): number => {
  // Average speed 500 mph + 30 min for takeoff/landing
  return Math.round((distance / 500) * 60 + 30);
};

// Seeded random for consistent results per flight
const seededRandom = (seed: string): number => {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    const char = seed.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash % 100) / 100;
};

export const generateFlightsForRoute = (
  origin: City,
  destination: City,
  matchDate: Date,
  matchId: string
): Flight[] => {
  const flights: Flight[] = [];
  const distance = calculateDistance(origin, destination);
  const daysUntilMatch = Math.ceil((matchDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));

  // Generate 3-5 flights per route
  const numFlights = 3 + Math.floor(seededRandom(matchId + origin.id) * 3);

  // Flight times: early morning to evening, 2 days before to match day
  const flightDays = [-2, -1, 0]; // D-2, D-1, D-0

  flightDays.forEach((dayOffset, dayIndex) => {
    const flightDate = new Date(matchDate);
    flightDate.setDate(flightDate.getDate() + dayOffset);

    // Generate 1-2 flights per day
    const flightsThisDay = dayIndex === 2 ? 1 : 1 + Math.floor(seededRandom(matchId + dayIndex.toString()) * 2);

    for (let i = 0; i < flightsThisDay && flights.length < numFlights; i++) {
      const departureHour = 6 + Math.floor(seededRandom(matchId + dayIndex.toString() + i) * 14); // 6 AM to 8 PM
      const departureTime = new Date(flightDate);
      departureTime.setHours(departureHour, Math.floor(Math.random() * 4) * 15, 0, 0);

      const duration = generateDuration(distance);
      const arrivalTime = new Date(departureTime.getTime() + duration * 60 * 1000);

      const airline = AIRLINES[Math.floor(seededRandom(matchId + i.toString()) * AIRLINES.length)];
      const riskStatus = generateRiskStatus();

      flights.push({
        id: `flight-${matchId}-${origin.id}-${flights.length}`,
        airline,
        flightNumber: generateFlightNumber(airline),
        origin,
        destination,
        departureTime,
        arrivalTime,
        price: generatePrice(distance, daysUntilMatch - dayOffset),
        seatsAvailable: Math.floor(Math.random() * 50) + 5,
        riskStatus,
        riskFactors: {
          weather: generateWeather(),
          historicalOnTime: riskStatus === 'on-time' ? 85 + Math.floor(Math.random() * 10) :
                            riskStatus === 'potential-delay' ? 65 + Math.floor(Math.random() * 15) :
                            45 + Math.floor(Math.random() * 15),
          distance
        }
      });
    }
  });

  // Sort by departure time
  return flights.sort((a, b) => a.departureTime.getTime() - b.departureTime.getTime());
};

export const isBookingWindowOpen = (matchDate: Date): { isOpen: boolean; opensAt: Date; closesAt: Date } => {
  const now = new Date();
  const matchTime = new Date(matchDate);

  // Opens 2 days before the match at midnight
  const opensAt = new Date(matchTime);
  opensAt.setDate(opensAt.getDate() - 2);
  opensAt.setHours(0, 0, 0, 0);

  // Closes 3 hours before kickoff
  const closesAt = new Date(matchTime);
  closesAt.setHours(closesAt.getHours() - 3);

  const isOpen = now >= opensAt && now <= closesAt;

  return { isOpen, opensAt, closesAt };
};
