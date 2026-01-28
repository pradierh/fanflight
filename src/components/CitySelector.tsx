'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { City } from '@/types';
import { HOST_CITIES } from '@/data/cities';

interface CitySelectorProps {
  selectedCity: City | null;
  onSelectCity: (city: City) => void;
}

const countryFlags: Record<City['country'], string> = {
  USA: '🇺🇸',
  Mexico: '🇲🇽',
  Canada: '🇨🇦',
};

export const CitySelector = ({ selectedCity, onSelectCity }: CitySelectorProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredCity, setHoveredCity] = useState<City | null>(null);

  const groupedCities = {
    USA: HOST_CITIES.filter(c => c.country === 'USA'),
    Mexico: HOST_CITIES.filter(c => c.country === 'Mexico'),
    Canada: HOST_CITIES.filter(c => c.country === 'Canada'),
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="w-full max-w-2xl mx-auto"
    >
      <div className="text-center mb-8">
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-3xl md:text-4xl font-bold text-white mb-3"
        >
          Where are you flying from?
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-white/60"
        >
          Select your home city to see available matches
        </motion.p>
      </div>

      <div className="relative">
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={() => setIsOpen(!isOpen)}
          className="w-full p-4 md:p-6 rounded-2xl glass text-left flex items-center justify-between group cursor-pointer"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[var(--wc-teal)] to-[var(--wc-teal-dark)] flex items-center justify-center text-2xl">
              {selectedCity ? countryFlags[selectedCity.country] : '🌎'}
            </div>
            <div>
              <p className="text-white/50 text-sm mb-1">I live in</p>
              <p className="text-white text-xl font-semibold">
                {selectedCity ? selectedCity.name : 'Select your city'}
              </p>
              {selectedCity && (
                <p className="text-white/40 text-sm">{selectedCity.airportCode}</p>
              )}
            </div>
          </div>
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-white/50 text-2xl"
          >
            ▾
          </motion.div>
        </motion.button>

        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -10, height: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute top-full left-0 right-0 mt-2 rounded-2xl glass overflow-hidden z-50"
            >
              <div className="max-h-[60vh] overflow-y-auto p-2">
                {Object.entries(groupedCities).map(([country, cities]) => (
                  <div key={country} className="mb-4 last:mb-0">
                    <div className="flex items-center gap-2 px-3 py-2 text-white/50 text-sm font-medium">
                      <span>{countryFlags[country as City['country']]}</span>
                      <span>{country}</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                      {cities.map((city) => (
                        <motion.button
                          key={city.id}
                          whileHover={{ scale: 1.02, x: 4 }}
                          whileTap={{ scale: 0.98 }}
                          onHoverStart={() => setHoveredCity(city)}
                          onHoverEnd={() => setHoveredCity(null)}
                          onClick={() => {
                            onSelectCity(city);
                            setIsOpen(false);
                          }}
                          className={`p-3 rounded-xl text-left transition-all cursor-pointer ${
                            selectedCity?.id === city.id
                              ? 'bg-[var(--wc-teal)]/20 border border-[var(--wc-teal)]/50'
                              : hoveredCity?.id === city.id
                              ? 'bg-white/10'
                              : 'bg-transparent'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-white font-medium">{city.name}</p>
                              <p className="text-white/40 text-xs">{city.stadium}</p>
                            </div>
                            <span className="text-white/30 text-sm font-mono">
                              {city.airportCode}
                            </span>
                          </div>
                        </motion.button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};
