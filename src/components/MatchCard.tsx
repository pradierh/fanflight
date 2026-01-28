'use client';

import { motion } from 'framer-motion';
import { Match } from '@/types';
import { formatDate, formatTime } from '@/lib/utils';
import { useCountdown } from '@/hooks/useCountdown';
import { isBookingWindowOpen } from '@/data/flights';

interface MatchCardProps {
  match: Match;
  onSelect: () => void;
  index: number;
}

export const MatchCard = ({ match, onSelect, index }: MatchCardProps) => {
  const bookingWindow = isBookingWindowOpen(match.date);
  const countdown = useCountdown(bookingWindow.closesAt);
  const opensCountdown = useCountdown(bookingWindow.opensAt);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      whileHover={{ scale: 1.02, y: -4 }}
      className="group cursor-pointer"
      onClick={onSelect}
    >
      <div className="relative rounded-2xl glass overflow-hidden">
        {/* Group Badge */}
        <div className="absolute top-4 right-4 px-3 py-1 rounded-full bg-[var(--wc-teal)]/20 border border-[var(--wc-teal)]/30">
          <span className="text-[var(--wc-teal)] text-xs font-semibold">
            Group {match.group}
          </span>
        </div>

        {/* Match Content */}
        <div className="p-6">
          {/* Teams */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex-1 text-center">
              <div className="text-4xl mb-2">{match.homeTeam.flag}</div>
              <p className="text-white font-semibold">{match.homeTeam.name}</p>
              <p className="text-white/40 text-sm">{match.homeTeam.code}</p>
            </div>

            <div className="px-6">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--wc-teal)] to-[var(--wc-coral)] flex items-center justify-center">
                <span className="text-white font-bold text-sm">VS</span>
              </div>
            </div>

            <div className="flex-1 text-center">
              <div className="text-4xl mb-2">{match.awayTeam.flag}</div>
              <p className="text-white font-semibold">{match.awayTeam.name}</p>
              <p className="text-white/40 text-sm">{match.awayTeam.code}</p>
            </div>
          </div>

          {/* Divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/20 to-transparent mb-4" />

          {/* Match Info */}
          <div className="flex items-center justify-between text-sm mb-4">
            <div className="flex items-center gap-2 text-white/60">
              <span>📅</span>
              <span>{formatDate(match.date)}</span>
            </div>
            <div className="flex items-center gap-2 text-white/60">
              <span>⏰</span>
              <span>{formatTime(match.date)}</span>
            </div>
          </div>

          {/* Venue */}
          <div className="flex items-center gap-2 text-white/70 text-sm mb-4">
            <span>🏟️</span>
            <span>{match.city.stadium}</span>
            <span className="text-white/40">•</span>
            <span className="text-[var(--wc-teal)]">{match.city.name}</span>
          </div>

          {/* Booking Window Status */}
          <div className={`rounded-xl p-3 ${
            bookingWindow.isOpen
              ? 'bg-[var(--wc-teal)]/10 border border-[var(--wc-teal)]/30'
              : 'bg-white/5 border border-white/10'
          }`}>
            {bookingWindow.isOpen ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[var(--wc-teal)] animate-pulse" />
                  <span className="text-[var(--wc-teal)] text-sm font-medium">Booking Open</span>
                </div>
                <div className="text-white/60 text-sm">
                  Closes in{' '}
                  <span className="text-[var(--wc-coral)] font-mono">
                    {countdown.days > 0 && `${countdown.days}d `}
                    {countdown.hours}h {countdown.minutes}m
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-white/50 text-sm">Booking opens</span>
                <span className="text-white/70 text-sm font-mono">
                  {opensCountdown.days > 0 && `${opensCountdown.days}d `}
                  {opensCountdown.hours}h {opensCountdown.minutes}m
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Book Button */}
        <motion.div
          initial={{ opacity: 0 }}
          whileHover={{ opacity: 1 }}
          className="absolute inset-0 bg-gradient-to-t from-[var(--wc-teal)]/80 to-transparent flex items-end justify-center pb-6 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <span className="px-6 py-2 rounded-full bg-white text-[var(--wc-navy)] font-semibold text-sm">
            View Flights →
          </span>
        </motion.div>
      </div>
    </motion.div>
  );
};
