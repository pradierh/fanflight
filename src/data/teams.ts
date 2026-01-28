import { Team } from '@/types';

export const TEAMS: Team[] = [
  { id: 'arg', name: 'Argentina', code: 'ARG', flag: '🇦🇷' },
  { id: 'bra', name: 'Brazil', code: 'BRA', flag: '🇧🇷' },
  { id: 'fra', name: 'France', code: 'FRA', flag: '🇫🇷' },
  { id: 'ger', name: 'Germany', code: 'GER', flag: '🇩🇪' },
  { id: 'eng', name: 'England', code: 'ENG', flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿' },
  { id: 'esp', name: 'Spain', code: 'ESP', flag: '🇪🇸' },
  { id: 'ita', name: 'Italy', code: 'ITA', flag: '🇮🇹' },
  { id: 'por', name: 'Portugal', code: 'POR', flag: '🇵🇹' },
  { id: 'ned', name: 'Netherlands', code: 'NED', flag: '🇳🇱' },
  { id: 'bel', name: 'Belgium', code: 'BEL', flag: '🇧🇪' },
  { id: 'usa', name: 'United States', code: 'USA', flag: '🇺🇸' },
  { id: 'mex', name: 'Mexico', code: 'MEX', flag: '🇲🇽' },
  { id: 'can', name: 'Canada', code: 'CAN', flag: '🇨🇦' },
  { id: 'jpn', name: 'Japan', code: 'JPN', flag: '🇯🇵' },
  { id: 'kor', name: 'South Korea', code: 'KOR', flag: '🇰🇷' },
  { id: 'aus', name: 'Australia', code: 'AUS', flag: '🇦🇺' },
  { id: 'mar', name: 'Morocco', code: 'MAR', flag: '🇲🇦' },
  { id: 'sen', name: 'Senegal', code: 'SEN', flag: '🇸🇳' },
  { id: 'cro', name: 'Croatia', code: 'CRO', flag: '🇭🇷' },
  { id: 'uru', name: 'Uruguay', code: 'URU', flag: '🇺🇾' },
];

export const getTeamById = (id: string): Team | undefined => {
  return TEAMS.find(team => team.id === id);
};
