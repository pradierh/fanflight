'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { City, Match, Flight, ViewState } from '@/types';
import {
  Header,
  CitySelector,
  MatchCard,
  MatchFilters,
  FlightCard,
  BookingConfirmation,
} from '@/components';
import { getUpcomingMatches } from '@/data/matches';
import { generateFlightsForRoute } from '@/data/flights';
import { formatDate } from '@/lib/utils';

export default function Home() {
  const [originCity, setOriginCity] = useState<City | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [selectedFlight, setSelectedFlight] = useState<Flight | null>(null);
  const [view, setView] = useState<ViewState>('city-select');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [filters, setFilters] = useState({ team: null as string | null, dateRange: 'all' });

  // Get matches excluding user's city
  const availableMatches = useMemo(() => {
    let matches = getUpcomingMatches(originCity?.id);

    // Apply team filter
    if (filters.team) {
      matches = matches.filter(
        (match) =>
          match.homeTeam.id === filters.team || match.awayTeam.id === filters.team
      );
    }

    // Apply date filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const weekEnd = new Date(today);
      weekEnd.setDate(weekEnd.getDate() + 7);

      matches = matches.filter((match) => {
        const matchDate = new Date(match.date);
        switch (filters.dateRange) {
          case 'today':
            return matchDate >= today && matchDate < tomorrow;
          case 'tomorrow':
            const dayAfterTomorrow = new Date(tomorrow);
            dayAfterTomorrow.setDate(dayAfterTomorrow.getDate() + 1);
            return matchDate >= tomorrow && matchDate < dayAfterTomorrow;
          case 'week':
            return matchDate >= today && matchDate < weekEnd;
          default:
            return true;
        }
      });
    }

    return matches;
  }, [originCity, filters]);

  // Generate flights for selected match
  const availableFlights = useMemo(() => {
    if (!originCity || !selectedMatch) return [];
    return generateFlightsForRoute(
      originCity,
      selectedMatch.city,
      selectedMatch.date,
      selectedMatch.id
    );
  }, [originCity, selectedMatch]);

  const handleCitySelect = (city: City) => {
    setOriginCity(city);
    setView('matches');
  };

  const handleMatchSelect = (match: Match) => {
    setSelectedMatch(match);
    setView('flights');
  };

  const handleFlightSelect = (flight: Flight) => {
    setSelectedFlight(flight);
    setShowConfirmation(true);
  };

  const handleBack = () => {
    if (view === 'flights') {
      setSelectedMatch(null);
      setView('matches');
    } else if (view === 'matches') {
      setView('city-select');
    }
  };

  const handleConfirmationClose = () => {
    setShowConfirmation(false);
    setSelectedFlight(null);
  };

  const handleBookingComplete = () => {
    setShowConfirmation(false);
    setSelectedFlight(null);
    setSelectedMatch(null);
    setView('matches');
  };

  return (
    <main className="min-h-screen">
      <Header />

      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-32 w-96 h-96 rounded-full bg-[var(--wc-teal)]/10 blur-3xl" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 rounded-full bg-[var(--wc-coral)]/10 blur-3xl" />
      </div>

      <div className="relative z-10 px-4 md:px-8 pb-12">
        <AnimatePresence mode="wait">
          {/* City Selection */}
          {view === 'city-select' && (
            <motion.div
              key="city-select"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, x: -50 }}
              className="max-w-7xl mx-auto pt-12 md:pt-20"
            >
              <CitySelector selectedCity={originCity} onSelectCity={handleCitySelect} />

              {/* Hero illustration */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="mt-16 text-center"
              >
                <div className="flex justify-center gap-8 text-6xl mb-8">
                  <motion.span
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    🇺🇸
                  </motion.span>
                  <motion.span
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0.3 }}
                  >
                    🇲🇽
                  </motion.span>
                  <motion.span
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0.6 }}
                  >
                    🇨🇦
                  </motion.span>
                </div>
                <p className="text-white/40 text-lg">
                  16 Host Cities • 48 Teams • Endless Possibilities
                </p>
              </motion.div>
            </motion.div>
          )}

          {/* Match Browser */}
          {view === 'matches' && (
            <motion.div
              key="matches"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              className="max-w-7xl mx-auto"
            >
              {/* Back Button & Title */}
              <div className="flex items-center gap-4 mb-6">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleBack}
                  className="w-10 h-10 rounded-xl glass flex items-center justify-center text-white/60 hover:text-white transition-colors cursor-pointer"
                >
                  ←
                </motion.button>
                <div>
                  <h2 className="text-2xl font-bold text-white">Upcoming Matches</h2>
                  <p className="text-white/60 text-sm">
                    Flying from {originCity?.name} ({originCity?.airportCode})
                  </p>
                </div>
              </div>

              {/* Filters */}
              <MatchFilters onFilterChange={setFilters} />

              {/* Match Grid */}
              {availableMatches.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {availableMatches.map((match, index) => (
                    <MatchCard
                      key={match.id}
                      match={match}
                      onSelect={() => handleMatchSelect(match)}
                      index={index}
                    />
                  ))}
                </div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-16"
                >
                  <div className="text-6xl mb-4">🔍</div>
                  <h3 className="text-xl font-semibold text-white mb-2">No Matches Found</h3>
                  <p className="text-white/60">Try adjusting your filters</p>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* Flight Selection */}
          {view === 'flights' && selectedMatch && (
            <motion.div
              key="flights"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              className="max-w-4xl mx-auto"
            >
              {/* Back Button & Match Summary */}
              <div className="flex items-center gap-4 mb-6">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleBack}
                  className="w-10 h-10 rounded-xl glass flex items-center justify-center text-white/60 hover:text-white transition-colors cursor-pointer"
                >
                  ←
                </motion.button>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-white">
                    Flights to {selectedMatch.city.name}
                  </h2>
                  <p className="text-white/60 text-sm">
                    {originCity?.airportCode} → {selectedMatch.city.airportCode}
                  </p>
                </div>
              </div>

              {/* Match Card Summary */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl glass p-4 mb-6"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="text-2xl">{selectedMatch.homeTeam.flag}</span>
                    <span className="text-white/40">vs</span>
                    <span className="text-2xl">{selectedMatch.awayTeam.flag}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-white font-medium">{formatDate(selectedMatch.date)}</p>
                    <p className="text-white/60 text-sm">{selectedMatch.city.stadium}</p>
                  </div>
                </div>
              </motion.div>

              {/* Flights List */}
              <div className="space-y-4">
                {availableFlights.map((flight, index) => (
                  <FlightCard
                    key={flight.id}
                    flight={flight}
                    onSelect={() => handleFlightSelect(flight)}
                    index={index}
                  />
                ))}
              </div>

              {availableFlights.length === 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-16"
                >
                  <div className="text-6xl mb-4">✈️</div>
                  <h3 className="text-xl font-semibold text-white mb-2">No Flights Available</h3>
                  <p className="text-white/60">Check back closer to the match date</p>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Booking Confirmation Modal */}
      {showConfirmation && selectedFlight && selectedMatch && (
        <BookingConfirmation
          flight={selectedFlight}
          match={selectedMatch}
          onClose={handleConfirmationClose}
          onConfirm={handleBookingComplete}
        />
      )}

      {/* Footer */}
      <footer className="relative z-10 py-8 text-center">
        <p className="text-white/30 text-sm">
          FIFA World Cup 2026™ • POC Demo • Not affiliated with FIFA
        </p>
      </footer>
    </main>
  );
}
