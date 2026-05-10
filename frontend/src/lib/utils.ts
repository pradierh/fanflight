import { FlightRiskStatus } from '@/types';

export const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date));
};

export const formatTime = (date: Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(date));
};

export const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
  }).format(price);
};

export const formatDuration = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
};

export const getFlightDuration = (departure: Date, arrival: Date): number => {
  return Math.round((new Date(arrival).getTime() - new Date(departure).getTime()) / (1000 * 60));
};

export const getRiskStatusColor = (status: FlightRiskStatus): string => {
  switch (status) {
    case 'on-time':
      return 'text-green-500';
    case 'potential-delay':
      return 'text-yellow-500';
    case 'high-risk':
      return 'text-red-500';
  }
};

export const getRiskStatusBgColor = (status: FlightRiskStatus): string => {
  switch (status) {
    case 'on-time':
      return 'bg-green-500/20 border-green-500/50';
    case 'potential-delay':
      return 'bg-yellow-500/20 border-yellow-500/50';
    case 'high-risk':
      return 'bg-red-500/20 border-red-500/50';
  }
};

export const getRiskStatusIcon = (status: FlightRiskStatus): string => {
  switch (status) {
    case 'on-time':
      return '🟢';
    case 'potential-delay':
      return '🟡';
    case 'high-risk':
      return '🔴';
  }
};

export const getRiskStatusLabel = (status: FlightRiskStatus): string => {
  switch (status) {
    case 'on-time':
      return 'On Time';
    case 'potential-delay':
      return 'Potential Delay';
    case 'high-risk':
      return 'High Risk';
  }
};

export const getWeatherIcon = (weather: 'clear' | 'cloudy' | 'rain' | 'storm'): string => {
  switch (weather) {
    case 'clear':
      return '☀️';
    case 'cloudy':
      return '☁️';
    case 'rain':
      return '🌧️';
    case 'storm':
      return '⛈️';
  }
};

export const cn = (...classes: (string | boolean | undefined)[]): string => {
  return classes.filter(Boolean).join(' ');
};
