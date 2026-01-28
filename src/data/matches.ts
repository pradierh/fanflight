import { Match } from '@/types';
import { HOST_CITIES } from './cities';
import { TEAMS } from './teams';

// Helper to create a date relative to today
const createMatchDate = (daysFromNow: number, hour: number): Date => {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  date.setHours(hour, 0, 0, 0);
  return date;
};

// Generate realistic group stage matches
export const MATCHES: Match[] = [
  // Group A
  {
    id: 'match-1',
    homeTeam: TEAMS[10], // USA
    awayTeam: TEAMS[13], // Japan
    city: HOST_CITIES[6], // Los Angeles
    date: createMatchDate(1, 18),
    group: 'A',
    stage: 'group'
  },
  {
    id: 'match-2',
    homeTeam: TEAMS[11], // Mexico
    awayTeam: TEAMS[17], // Senegal
    city: HOST_CITIES[7], // Mexico City
    date: createMatchDate(1, 21),
    group: 'A',
    stage: 'group'
  },
  // Group B
  {
    id: 'match-3',
    homeTeam: TEAMS[0], // Argentina
    awayTeam: TEAMS[15], // Australia
    city: HOST_CITIES[8], // Miami
    date: createMatchDate(2, 15),
    group: 'B',
    stage: 'group'
  },
  {
    id: 'match-4',
    homeTeam: TEAMS[1], // Brazil
    awayTeam: TEAMS[14], // South Korea
    city: HOST_CITIES[4], // Houston
    date: createMatchDate(2, 18),
    group: 'B',
    stage: 'group'
  },
  // Group C
  {
    id: 'match-5',
    homeTeam: TEAMS[2], // France
    awayTeam: TEAMS[16], // Morocco
    city: HOST_CITIES[10], // New York
    date: createMatchDate(2, 21),
    group: 'C',
    stage: 'group'
  },
  {
    id: 'match-6',
    homeTeam: TEAMS[4], // England
    awayTeam: TEAMS[12], // Canada
    city: HOST_CITIES[14], // Toronto
    date: createMatchDate(3, 14),
    group: 'C',
    stage: 'group'
  },
  // Group D
  {
    id: 'match-7',
    homeTeam: TEAMS[3], // Germany
    awayTeam: TEAMS[18], // Croatia
    city: HOST_CITIES[2], // Dallas
    date: createMatchDate(3, 17),
    group: 'D',
    stage: 'group'
  },
  {
    id: 'match-8',
    homeTeam: TEAMS[5], // Spain
    awayTeam: TEAMS[9], // Belgium
    city: HOST_CITIES[0], // Atlanta
    date: createMatchDate(3, 20),
    group: 'D',
    stage: 'group'
  },
  // More exciting matchups
  {
    id: 'match-9',
    homeTeam: TEAMS[7], // Portugal
    awayTeam: TEAMS[19], // Uruguay
    city: HOST_CITIES[13], // Seattle
    date: createMatchDate(4, 16),
    group: 'E',
    stage: 'group'
  },
  {
    id: 'match-10',
    homeTeam: TEAMS[6], // Italy
    awayTeam: TEAMS[8], // Netherlands
    city: HOST_CITIES[12], // San Francisco
    date: createMatchDate(4, 19),
    group: 'E',
    stage: 'group'
  },
  {
    id: 'match-11',
    homeTeam: TEAMS[10], // USA
    awayTeam: TEAMS[4], // England
    city: HOST_CITIES[11], // Philadelphia
    date: createMatchDate(5, 18),
    group: 'F',
    stage: 'group'
  },
  {
    id: 'match-12',
    homeTeam: TEAMS[0], // Argentina
    awayTeam: TEAMS[2], // France
    city: HOST_CITIES[5], // Kansas City
    date: createMatchDate(5, 21),
    group: 'F',
    stage: 'group'
  },
  {
    id: 'match-13',
    homeTeam: TEAMS[1], // Brazil
    awayTeam: TEAMS[3], // Germany
    city: HOST_CITIES[1], // Boston
    date: createMatchDate(6, 15),
    group: 'G',
    stage: 'group'
  },
  {
    id: 'match-14',
    homeTeam: TEAMS[11], // Mexico
    awayTeam: TEAMS[10], // USA
    city: HOST_CITIES[3], // Guadalajara
    date: createMatchDate(7, 20),
    group: 'G',
    stage: 'group'
  },
  {
    id: 'match-15',
    homeTeam: TEAMS[12], // Canada
    awayTeam: TEAMS[11], // Mexico
    city: HOST_CITIES[15], // Vancouver
    date: createMatchDate(8, 17),
    group: 'H',
    stage: 'group'
  }
];

export const getMatchById = (id: string): Match | undefined => {
  return MATCHES.find(match => match.id === id);
};

export const getMatchesByCity = (cityId: string): Match[] => {
  return MATCHES.filter(match => match.city.id === cityId);
};

export const getUpcomingMatches = (excludeCityId?: string): Match[] => {
  const now = new Date();
  return MATCHES
    .filter(match => {
      const matchTime = new Date(match.date);
      return matchTime > now && (excludeCityId ? match.city.id !== excludeCityId : true);
    })
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
};
