const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const fetchMatches = async () => {
  const res = await fetch(`${API_URL}/api/matches`);
  if (!res.ok) throw new Error('Erreur matchs');
  return res.json();
};

export const fetchFlights = async (matchId: number, departureCity: string) => {
  const res = await fetch(
    `${API_URL}/api/flights/${matchId}?departure_city=${encodeURIComponent(departureCity)}`
  );
  if (!res.ok) throw new Error('Erreur vols');
  return res.json();
};

export const fetchCities = async () => {
  const res = await fetch(`${API_URL}/api/cities`);
  if (!res.ok) throw new Error('Erreur villes');
  return res.json();
};

export const fetchTeams = async () => {
  const res = await fetch(`${API_URL}/api/teams`);
  if (!res.ok) throw new Error('Erreur équipes');
  return res.json();
};