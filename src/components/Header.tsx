'use client';

import { motion } from 'framer-motion';

export const Header = () => {
  return (
    <header className="relative py-6 px-4 md:px-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-7xl mx-auto flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--wc-teal)] to-[var(--wc-coral)] flex items-center justify-center">
            <span className="text-2xl">✈️</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">
              Fan<span className="gradient-text">Flight</span>
            </h1>
            <p className="text-xs text-white/60">World Cup 2026</p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-6">
          <nav className="flex items-center gap-4 text-sm text-white/70">
            <span className="px-3 py-1.5 rounded-full bg-white/10 text-white">
              Flights
            </span>
            <span className="hover:text-white cursor-pointer transition-colors">
              My Bookings
            </span>
            <span className="hover:text-white cursor-pointer transition-colors">
              Help
            </span>
          </nav>
        </div>

        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.3, type: 'spring' }}
          className="flex items-center gap-2 px-4 py-2 rounded-full glass text-white text-sm"
        >
          <span className="w-2 h-2 rounded-full bg-[var(--wc-teal)] animate-pulse" />
          <span>Live Availability</span>
        </motion.div>
      </motion.div>
    </header>
  );
};
