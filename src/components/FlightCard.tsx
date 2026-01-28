'use client';

import { motion } from 'framer-motion';
import { Flight } from '@/types';
import {
  formatTime,
  formatPrice,
  formatDuration,
  getFlightDuration,
  getRiskStatusIcon,
  getRiskStatusLabel,
  getRiskStatusBgColor,
  getWeatherIcon,
} from '@/lib/utils';

interface FlightCardProps {
  flight: Flight;
  onSelect: () => void;
  index: number;
}

export const FlightCard = ({ flight, onSelect, index }: FlightCardProps) => {
  const duration = getFlightDuration(flight.departureTime, flight.arrivalTime);

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
          {/* Airline & Flight Info */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                <span className="text-xl">✈️</span>
              </div>
              <div>
                <p className="text-white font-medium">{flight.airline}</p>
                <p className="text-white/40 text-sm font-mono">{flight.flightNumber}</p>
              </div>
            </div>

            {/* Risk Status Badge */}
            <div className={`px-3 py-1.5 rounded-full border ${getRiskStatusBgColor(flight.riskStatus)}`}>
              <span className="text-sm">
                {getRiskStatusIcon(flight.riskStatus)} {getRiskStatusLabel(flight.riskStatus)}
              </span>
            </div>
          </div>

          {/* Flight Times */}
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1">
              <p className="text-2xl font-bold text-white">{formatTime(flight.departureTime)}</p>
              <p className="text-white/60 text-sm">{flight.origin.airportCode}</p>
            </div>

            <div className="flex-1 flex flex-col items-center">
              <p className="text-white/40 text-xs mb-1">{formatDuration(duration)}</p>
              <div className="w-full flex items-center gap-1">
                <div className="h-0.5 flex-1 bg-white/20 rounded" />
                <span className="text-white/30 text-xs">✈️</span>
                <div className="h-0.5 flex-1 bg-white/20 rounded" />
              </div>
              <p className="text-white/40 text-xs mt-1">Direct</p>
            </div>

            <div className="flex-1 text-right">
              <p className="text-2xl font-bold text-white">{formatTime(flight.arrivalTime)}</p>
              <p className="text-white/60 text-sm">{flight.destination.airportCode}</p>
            </div>
          </div>

          {/* Risk Factors */}
          <div className="flex items-center gap-3 mb-4 p-3 rounded-xl bg-white/5">
            <div className="flex items-center gap-1.5 text-sm">
              <span>{getWeatherIcon(flight.riskFactors.weather)}</span>
              <span className="text-white/60 capitalize">{flight.riskFactors.weather}</span>
            </div>
            <div className="w-px h-4 bg-white/20" />
            <div className="flex items-center gap-1.5 text-sm">
              <span>📊</span>
              <span className="text-white/60">{flight.riskFactors.historicalOnTime}% on-time</span>
            </div>
            <div className="w-px h-4 bg-white/20" />
            <div className="flex items-center gap-1.5 text-sm">
              <span>📍</span>
              <span className="text-white/60">{flight.riskFactors.distance.toLocaleString()} mi</span>
            </div>
          </div>

          {/* Price & Book */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold gradient-text">{formatPrice(flight.price)}</p>
              <p className="text-white/40 text-sm">{flight.seatsAvailable} seats left</p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-[var(--wc-teal)] to-[var(--wc-teal-dark)] text-white font-semibold shadow-lg shadow-[var(--wc-teal)]/30 hover:shadow-[var(--wc-teal)]/50 transition-shadow"
            >
              Select Flight
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
