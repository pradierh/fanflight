'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Flight, Match } from '@/types';
import {
  formatDate,
  formatTime,
  formatPrice,
  formatDuration,
  getFlightDuration,
  getRiskStatusIcon,
} from '@/lib/utils';
import { useState } from 'react';

interface BookingConfirmationProps {
  flight: Flight;
  match: Match;
  onClose: () => void;
  onConfirm: () => void;
}

export const BookingConfirmation = ({
  flight,
  match,
  onClose,
  onConfirm,
}: BookingConfirmationProps) => {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const duration = getFlightDuration(flight.departureTime, flight.arrivalTime);

  const handleConfirm = async () => {
    setIsConfirming(true);
    // Simulate booking process
    await new Promise(resolve => setTimeout(resolve, 2000));
    setIsConfirming(false);
    setIsConfirmed(true);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-lg rounded-3xl glass overflow-hidden"
        >
          {!isConfirmed ? (
            <>
              {/* Header */}
              <div className="relative p-6 bg-gradient-to-r from-[var(--wc-teal)] to-[var(--wc-coral)]">
                <button
                  onClick={onClose}
                  className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white hover:bg-white/30 transition-colors cursor-pointer"
                >
                  ✕
                </button>
                <h2 className="text-2xl font-bold text-white mb-1">Confirm Your Booking</h2>
                <p className="text-white/80">Review your flight details</p>
              </div>

              {/* Content */}
              <div className="p-6">
                {/* Match Info */}
                <div className="flex items-center justify-center gap-4 mb-6 p-4 rounded-xl bg-white/5">
                  <div className="text-center">
                    <span className="text-3xl">{match.homeTeam.flag}</span>
                    <p className="text-white/60 text-sm mt-1">{match.homeTeam.code}</p>
                  </div>
                  <div className="text-white/40 font-bold">VS</div>
                  <div className="text-center">
                    <span className="text-3xl">{match.awayTeam.flag}</span>
                    <p className="text-white/60 text-sm mt-1">{match.awayTeam.code}</p>
                  </div>
                </div>

                {/* Flight Details */}
                <div className="space-y-4 mb-6">
                  <div className="flex items-center justify-between">
                    <span className="text-white/60">Flight</span>
                    <span className="text-white font-medium">{flight.airline} {flight.flightNumber}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white/60">Route</span>
                    <span className="text-white font-medium">{flight.origin.airportCode} → {flight.destination.airportCode}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white/60">Date</span>
                    <span className="text-white font-medium">{formatDate(flight.departureTime)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white/60">Departure</span>
                    <span className="text-white font-medium">{formatTime(flight.departureTime)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white/60">Duration</span>
                    <span className="text-white font-medium">{formatDuration(duration)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white/60">Status</span>
                    <span className="text-white font-medium">
                      {getRiskStatusIcon(flight.riskStatus)} {flight.riskStatus.replace('-', ' ')}
                    </span>
                  </div>
                </div>

                {/* Divider */}
                <div className="h-px bg-white/10 mb-6" />

                {/* Price */}
                <div className="flex items-center justify-between mb-6">
                  <span className="text-white text-lg">Total Price</span>
                  <span className="text-3xl font-bold gradient-text">{formatPrice(flight.price)}</span>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    className="flex-1 py-3 rounded-xl border border-white/20 text-white font-medium hover:bg-white/10 transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleConfirm}
                    disabled={isConfirming}
                    className="flex-1 py-3 rounded-xl bg-gradient-to-r from-[var(--wc-teal)] to-[var(--wc-teal-dark)] text-white font-semibold shadow-lg disabled:opacity-50 cursor-pointer"
                  >
                    {isConfirming ? (
                      <span className="flex items-center justify-center gap-2">
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        >
                          ⏳
                        </motion.span>
                        Booking...
                      </span>
                    ) : (
                      'Confirm Booking'
                    )}
                  </motion.button>
                </div>
              </div>
            </>
          ) : (
            /* Success State */
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="p-8 text-center"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', delay: 0.2 }}
                className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-r from-[var(--wc-teal)] to-[var(--wc-teal-dark)] flex items-center justify-center"
              >
                <span className="text-4xl">✓</span>
              </motion.div>
              <h2 className="text-2xl font-bold text-white mb-2">Booking Confirmed!</h2>
              <p className="text-white/60 mb-6">
                Your flight to {match.city.name} has been booked.
              </p>
              <div className="p-4 rounded-xl bg-white/5 mb-6">
                <p className="text-white/80 text-sm">Confirmation Number</p>
                <p className="text-xl font-mono font-bold gradient-text">
                  WC26-{Math.random().toString(36).substring(2, 8).toUpperCase()}
                </p>
              </div>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onConfirm}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--wc-teal)] to-[var(--wc-teal-dark)] text-white font-semibold cursor-pointer"
              >
                Done
              </motion.button>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
