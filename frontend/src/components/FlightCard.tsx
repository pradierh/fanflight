'use client';

import { motion } from 'framer-motion';
import { Flight } from '@/types';
import { formatPrice } from '@/lib/utils';

interface FlightCardProps {
  flight: Flight;
  onSelect: () => void;
  index: number;
}

const DelayBadge = ({ probability }: { probability: number | null }) => {
  if (probability === null || probability === undefined) return null;

  const pct = Math.round(probability * 100);

  const config =
    pct < 20
      ? { label: 'Faible risque de retard', color: 'text-green-400', bg: 'bg-green-400/10', dot: 'bg-green-400' }
      : pct < 50
      ? { label: 'Risque modéré', color: 'text-orange-400', bg: 'bg-orange-400/10', dot: 'bg-orange-400' }
      : { label: 'Risque élevé de retard', color: 'text-red-400', bg: 'bg-red-400/10', dot: 'bg-red-400' };

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${config.bg} w-fit`}>
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      <span className={`text-xs font-medium ${config.color}`}>
        {config.label} — {pct}%
      </span>
    </div>
  );
};

export const FlightCard = ({ flight, onSelect, index }: FlightCardProps) => {

  const formatTime = (timeStr: string) =>
    new Date(timeStr).toLocaleTimeString('fr-FR', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      whileHover={{ scale: 1.01 }}
      className="group cursor-pointer"
      onClick={onSelect}
    >
      <div className="rounded-2xl glass overflow-hidden hover:border-[var(--wc-teal)]/50 transition-all">
        <div className="p-4 md:p-6">

          {/* Airline + delay badge */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                <span className="text-xl">✈️</span>
              </div>
              <div>
                <p className="text-white font-medium">{flight.airline}</p>
                {flight.nb_escales > 0 && (
                  <p className="text-orange-400 text-xs">{flight.nb_escales} escale{flight.nb_escales > 1 ? 's' : ''}</p>
                )}
                {flight.nb_escales === 0 && (
                  <p className="text-green-400 text-xs">Direct</p>
                )}
              </div>
            </div>
            <DelayBadge probability={flight.delay_probability} />
          </div>

          {/* Segments */}
          {flight.segments.map((segment, i) => (
            <div key={i} className="mb-2">
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-xl font-bold text-white">{formatTime(segment.departure_airport_time)}</p>
                  <p className="text-white/60 text-sm">{segment.departure_airport_code}</p>
                  <p className="text-white/40 text-xs">{segment.departure_city}</p>
                </div>

                <div className="flex flex-col items-center">
                  <p className="text-white/40 text-xs mb-1">{segment.duration} min</p>
                  <div className="flex items-center gap-1">
                    <div className="h-0.5 w-8 bg-white/20 rounded" />
                    <span className="text-white/30 text-xs">✈️</span>
                    <div className="h-0.5 w-8 bg-white/20 rounded" />
                  </div>
                </div>

                <div className="flex-1 text-right">
                  <p className="text-xl font-bold text-white">{formatTime(segment.arrival_airport_time)}</p>
                  <p className="text-white/60 text-sm">{segment.arrival_airport_code}</p>
                  <p className="text-white/40 text-xs">{segment.arrival_city}</p>
                </div>
              </div>

              {i < flight.segments.length - 1 && (
                <div className="flex items-center gap-2 my-2 px-2">
                  <div className="h-px flex-1 bg-white/10" />
                  <span className="text-orange-400 text-xs">
                    ⏱ Escale {segment.layover_duration} min — {segment.arrival_airport_code}
                  </span>
                  <div className="h-px flex-1 bg-white/10" />
                </div>
              )}
            </div>
          ))}

          {/* Price & Book */}
          <div className="flex items-center justify-between mt-4">
            <p className="text-3xl font-bold gradient-text">{formatPrice(flight.price)}</p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-[var(--wc-teal)] to-[var(--wc-teal-dark)] text-white font-semibold"
            >
              Select Flight
            </motion.button>
          </div>

        </div>
      </div>
    </motion.div>
  );
};