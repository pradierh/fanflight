'use client';

import { motion } from 'framer-motion';
import { Flight } from '@/types';
import { formatPrice } from '@/lib/utils';

interface FlightCardProps {
  flight: Flight;
  onSelect: () => void;
  index: number;
}

export const FlightCard = ({ flight, onSelect, index }: FlightCardProps) => {

  const formatTime = (timeStr: string) =>
    new Date(timeStr).toLocaleTimeString('fr-FR', {     day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })

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

          {/* Airline */}
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
          </div>

          {/* Segments */}
          {flight.segments.map((segment, i) => (
            <div key={i} className="mb-2">
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-xl font-bold text-white">{formatTime(segment.departure_airport_time)}</p>
                  <p className="text-white/60 text-sm">{segment.departure_airport_id}</p>
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
                  <p className="text-white/60 text-sm">{segment.arrival_airport_id}</p>
                  <p className="text-white/40 text-xs">{segment.arrival_city}</p>
                </div>
              </div>

              {/* Escale entre deux segments */}
              {i < flight.segments.length - 1 && (
                <div className="flex items-center gap-2 my-2 px-2">
                  <div className="h-px flex-1 bg-white/10" />
                  <span className="text-orange-400 text-xs">
                    ⏱ Escale {segment.layover_duration} min — {segment.arrival_airport_id}
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
  )
}