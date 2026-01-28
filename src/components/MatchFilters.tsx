'use client';

import { motion } from 'framer-motion';
import { useState } from 'react';
import { Team } from '@/types';
import { TEAMS } from '@/data/teams';

interface MatchFiltersProps {
  onFilterChange: (filters: { team: string | null; dateRange: string }) => void;
}

export const MatchFilters = ({ onFilterChange }: MatchFiltersProps) => {
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState('all');
  const [showTeamDropdown, setShowTeamDropdown] = useState(false);

  const dateRanges = [
    { id: 'all', label: 'All Dates' },
    { id: 'today', label: 'Today' },
    { id: 'tomorrow', label: 'Tomorrow' },
    { id: 'week', label: 'This Week' },
  ];

  const handleTeamSelect = (teamId: string | null) => {
    setSelectedTeam(teamId);
    setShowTeamDropdown(false);
    onFilterChange({ team: teamId, dateRange });
  };

  const handleDateChange = (range: string) => {
    setDateRange(range);
    onFilterChange({ team: selectedTeam, dateRange: range });
  };

  const selectedTeamData = selectedTeam ? TEAMS.find(t => t.id === selectedTeam) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-wrap items-center gap-3 mb-6"
    >
      {/* Date Filter */}
      <div className="flex items-center gap-1 p-1 rounded-xl glass">
        {dateRanges.map((range) => (
          <button
            key={range.id}
            onClick={() => handleDateChange(range.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              dateRange === range.id
                ? 'bg-[var(--wc-teal)] text-white'
                : 'text-white/60 hover:text-white hover:bg-white/10'
            }`}
          >
            {range.label}
          </button>
        ))}
      </div>

      {/* Team Filter */}
      <div className="relative">
        <button
          onClick={() => setShowTeamDropdown(!showTeamDropdown)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass text-white/80 hover:text-white transition-colors cursor-pointer"
        >
          {selectedTeamData ? (
            <>
              <span className="text-lg">{selectedTeamData.flag}</span>
              <span className="text-sm font-medium">{selectedTeamData.name}</span>
            </>
          ) : (
            <>
              <span>🔍</span>
              <span className="text-sm">Filter by Team</span>
            </>
          )}
          <span className="text-white/40 ml-1">▾</span>
        </button>

        {showTeamDropdown && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute top-full left-0 mt-2 w-64 rounded-xl glass overflow-hidden z-50"
          >
            <div className="max-h-60 overflow-y-auto p-2">
              <button
                onClick={() => handleTeamSelect(null)}
                className="w-full px-3 py-2 text-left text-sm text-white/60 hover:bg-white/10 rounded-lg transition-colors cursor-pointer"
              >
                All Teams
              </button>
              {TEAMS.map((team) => (
                <button
                  key={team.id}
                  onClick={() => handleTeamSelect(team.id)}
                  className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 rounded-lg transition-colors cursor-pointer ${
                    selectedTeam === team.id
                      ? 'bg-[var(--wc-teal)]/20 text-white'
                      : 'text-white/80 hover:bg-white/10'
                  }`}
                >
                  <span className="text-lg">{team.flag}</span>
                  <span>{team.name}</span>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </div>

      {/* Clear Filters */}
      {(selectedTeam || dateRange !== 'all') && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={() => {
            setSelectedTeam(null);
            setDateRange('all');
            onFilterChange({ team: null, dateRange: 'all' });
          }}
          className="px-3 py-2 text-sm text-[var(--wc-coral)] hover:text-white transition-colors cursor-pointer"
        >
          Clear Filters ✕
        </motion.button>
      )}
    </motion.div>
  );
};
