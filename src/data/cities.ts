import { City } from '@/types';

export const HOST_CITIES: City[] = [
  {
    id: 'atlanta',
    name: 'Atlanta',
    country: 'USA',
    stadium: 'Mercedes-Benz Stadium',
    airportCode: 'ATL',
    coordinates: { lat: 33.7490, lng: -84.3880 }
  },
  {
    id: 'boston',
    name: 'Boston',
    country: 'USA',
    stadium: 'Gillette Stadium',
    airportCode: 'BOS',
    coordinates: { lat: 42.3601, lng: -71.0589 }
  },
  {
    id: 'dallas',
    name: 'Dallas',
    country: 'USA',
    stadium: 'AT&T Stadium',
    airportCode: 'DFW',
    coordinates: { lat: 32.7767, lng: -96.7970 }
  },
  {
    id: 'guadalajara',
    name: 'Guadalajara',
    country: 'Mexico',
    stadium: 'Estadio Akron',
    airportCode: 'GDL',
    coordinates: { lat: 20.6597, lng: -103.3496 }
  },
  {
    id: 'houston',
    name: 'Houston',
    country: 'USA',
    stadium: 'NRG Stadium',
    airportCode: 'IAH',
    coordinates: { lat: 29.7604, lng: -95.3698 }
  },
  {
    id: 'kansas-city',
    name: 'Kansas City',
    country: 'USA',
    stadium: 'GEHA Field at Arrowhead Stadium',
    airportCode: 'MCI',
    coordinates: { lat: 39.0997, lng: -94.5786 }
  },
  {
    id: 'los-angeles',
    name: 'Los Angeles',
    country: 'USA',
    stadium: 'SoFi Stadium',
    airportCode: 'LAX',
    coordinates: { lat: 34.0522, lng: -118.2437 }
  },
  {
    id: 'mexico-city',
    name: 'Mexico City',
    country: 'Mexico',
    stadium: 'Estadio Azteca',
    airportCode: 'MEX',
    coordinates: { lat: 19.4326, lng: -99.1332 }
  },
  {
    id: 'miami',
    name: 'Miami',
    country: 'USA',
    stadium: 'Hard Rock Stadium',
    airportCode: 'MIA',
    coordinates: { lat: 25.7617, lng: -80.1918 }
  },
  {
    id: 'monterrey',
    name: 'Monterrey',
    country: 'Mexico',
    stadium: 'Estadio BBVA',
    airportCode: 'MTY',
    coordinates: { lat: 25.6866, lng: -100.3161 }
  },
  {
    id: 'new-york',
    name: 'New York/New Jersey',
    country: 'USA',
    stadium: 'MetLife Stadium',
    airportCode: 'EWR',
    coordinates: { lat: 40.7128, lng: -74.0060 }
  },
  {
    id: 'philadelphia',
    name: 'Philadelphia',
    country: 'USA',
    stadium: 'Lincoln Financial Field',
    airportCode: 'PHL',
    coordinates: { lat: 39.9526, lng: -75.1652 }
  },
  {
    id: 'san-francisco',
    name: 'San Francisco Bay Area',
    country: 'USA',
    stadium: "Levi's Stadium",
    airportCode: 'SFO',
    coordinates: { lat: 37.7749, lng: -122.4194 }
  },
  {
    id: 'seattle',
    name: 'Seattle',
    country: 'USA',
    stadium: 'Lumen Field',
    airportCode: 'SEA',
    coordinates: { lat: 47.6062, lng: -122.3321 }
  },
  {
    id: 'toronto',
    name: 'Toronto',
    country: 'Canada',
    stadium: 'BMO Field',
    airportCode: 'YYZ',
    coordinates: { lat: 43.6532, lng: -79.3832 }
  },
  {
    id: 'vancouver',
    name: 'Vancouver',
    country: 'Canada',
    stadium: 'BC Place',
    airportCode: 'YVR',
    coordinates: { lat: 49.2827, lng: -123.1207 }
  }
];

export const getCityById = (id: string): City | undefined => {
  return HOST_CITIES.find(city => city.id === id);
};

export const getCitiesByCountry = (country: City['country']): City[] => {
  return HOST_CITIES.filter(city => city.country === country);
};
