import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SlidersHorizontal, X, ChevronDown, Wallet, Globe, MapPin, Clock, RotateCcw, Eye, Star } from 'lucide-react'
import { useWebsites, useTargets } from '../hooks/useApartments'
import CustomDropdown from './CustomDropdown'
import MultiSelectDropdown from './MultiSelectDropdown'

export default function FilterBar({ filters, onFilterChange }) {
  const { websites } = useWebsites()
  const { targets } = useTargets()
  const [isExpanded, setIsExpanded] = useState(true)
  
  // Local state for input values (for immediate UI feedback)
  const [localMinPrice, setLocalMinPrice] = useState(filters.minPrice || '')
  const [localMaxPrice, setLocalMaxPrice] = useState(filters.maxPrice || '')
  const [localMinTime, setLocalMinTime] = useState(filters.minTime || '')
  const [localMaxTime, setLocalMaxTime] = useState(filters.maxTime || '')
  
  // Refs for debounce timers
  const minPriceTimer = useRef(null)
  const maxPriceTimer = useRef(null)
  const minTimeTimer = useRef(null)
  const maxTimeTimer = useRef(null)
  
  // Sync local state with filters when they change externally (e.g., Clear Filters)
  useEffect(() => {
    setLocalMinPrice(filters.minPrice || '')
    setLocalMaxPrice(filters.maxPrice || '')
    setLocalMinTime(filters.minTime || '')
    setLocalMaxTime(filters.maxTime || '')
  }, [filters.minPrice, filters.maxPrice, filters.minTime, filters.maxTime])

  const handleDebouncedChange = (key, value, setLocal, timerRef) => {
    // Update local state immediately for UI feedback
    setLocal(value)
    
    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }
    
    // Set new timer to apply filter after 1 second
    timerRef.current = setTimeout(() => {
      onFilterChange({ [key]: value ? parseInt(value) : null })
    }, 1000)
  }

  const handleClearFilters = () => {
    onFilterChange({
      minPrice: null,
      maxPrice: null,
      websites: [],
      targetId: targets[0]?.id || null,
      minTime: null,
      maxTime: null,
      showSeen: true,
      showOnlyFavorites: false,
    })
  }

  const hasActiveFilters = filters.minPrice || filters.maxPrice || (filters.websites && filters.websites.length > 0) || filters.minTime || filters.maxTime || filters.showSeen === false || filters.showOnlyFavorites

  return (
    <motion.div
      className="glass-card rounded-2xl overflow-visible relative z-[60]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
    >
      {/* Header */}
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/30 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-violet-400 to-indigo-500 rounded-xl">
            <SlidersHorizontal className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-gray-800">Filter Apartments</h3>
            <p className="text-xs text-gray-500">
              {hasActiveFilters ? 'Filters active' : 'Refine your search'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <motion.button
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="p-2 hover:bg-violet-100 rounded-xl transition-colors text-violet-500"
              onClick={(e) => {
                e.stopPropagation()
                handleClearFilters()
              }}
              title="Clear all filters"
            >
              <RotateCcw className="w-4 h-4" />
            </motion.button>
          )}
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-5 h-5 text-gray-400" />
          </motion.div>
        </div>
      </div>

      {/* Filters */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="px-4 pb-4">
              <div className="h-px bg-gradient-to-r from-transparent via-violet-200 to-transparent mb-4" />
              
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                {/* Min Price */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
                    <Wallet className="w-4 h-4 text-violet-400" />
                    Min Price
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">¥</span>
                    <input
                      type="number"
                      placeholder="50,000"
                      className="w-full pl-7 pr-3 py-2.5 bg-white/50 border-2 border-gray-100 rounded-xl text-sm focus:border-violet-300 transition-colors"
                      value={localMinPrice}
                      onChange={(e) => handleDebouncedChange('minPrice', e.target.value, setLocalMinPrice, minPriceTimer)}
                    />
                  </div>
                </div>

                {/* Max Price */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
                    <Wallet className="w-4 h-4 text-indigo-400" />
                    Max Price
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">¥</span>
                    <input
                      type="number"
                      placeholder="150,000"
                      className="w-full pl-7 pr-3 py-2.5 bg-white/50 border-2 border-gray-100 rounded-xl text-sm focus:border-indigo-300 transition-colors"
                      value={localMaxPrice}
                      onChange={(e) => handleDebouncedChange('maxPrice', e.target.value, setLocalMaxPrice, maxPriceTimer)}
                    />
                  </div>
                </div>

                {/* Website Filter - Multi-select */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
                    <Globe className="w-4 h-4 text-blue-400" />
                    Websites
                  </label>
                  <MultiSelectDropdown
                    options={websites.map((w) => ({ value: w.name, label: w.name }))}
                    selectedValues={filters.websites || []}
                    onChange={(values) => onFilterChange({ websites: values })}
                    placeholder="Select websites..."
                    icon={Globe}
                  />
                </div>

                {/* Target Filter */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
                    <MapPin className="w-4 h-4 text-emerald-400" />
                    Destination
                  </label>
                  <CustomDropdown
                    value={filters.targetId || ''}
                    onChange={(value) => onFilterChange({ targetId: value ? parseInt(value) : null })}
                    options={targets.map((t) => ({ value: t.id, label: t.name }))}
                    placeholder="Select Destination"
                    icon={MapPin}
                  />
                </div>

                {/* Min Commute Time */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
                    <Clock className="w-4 h-4 text-amber-300" />
                    Min Commute
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      placeholder="0"
                      className="w-full pl-3 pr-12 py-2.5 bg-white/50 border-2 border-gray-100 rounded-xl text-sm focus:border-amber-200 transition-colors"
                      value={localMinTime}
                      onChange={(e) => handleDebouncedChange('minTime', e.target.value, setLocalMinTime, minTimeTimer)}
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">min</span>
                  </div>
                </div>

                {/* Max Commute Time */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
                    <Clock className="w-4 h-4 text-amber-400" />
                    Max Commute
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      placeholder="60"
                      className="w-full pl-3 pr-12 py-2.5 bg-white/50 border-2 border-gray-100 rounded-xl text-sm focus:border-amber-300 transition-colors"
                      value={localMaxTime}
                      onChange={(e) => handleDebouncedChange('maxTime', e.target.value, setLocalMaxTime, maxTimeTimer)}
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">min</span>
                  </div>
                </div>
              </div>
              
              {/* Second Row - Filter Chips */}
              <div className="flex flex-wrap items-center gap-3 mt-4 pt-4 border-t border-gray-100">
                {/* Show Seen APTs Chip */}
                <button
                  onClick={() => onFilterChange({ showSeen: filters.showSeen === false ? true : false })}
                  className={`filter-chip filter-chip-seen ${filters.showSeen !== false ? 'active' : ''}`}
                >
                  <Eye className="w-4 h-4" />
                  Show Seen APTs
                </button>
                
                {/* Show Only Seen Chip */}
                <button
                  onClick={() => onFilterChange({ showOnlySeen: !filters.showOnlySeen })}
                  className={`filter-chip filter-chip-seen ${filters.showOnlySeen ? 'active' : ''}`}
                >
                  <Eye className="w-4 h-4" />
                  Show Only Seen
                </button>
                
                {/* Show Only Favorites Chip */}
                <button
                  onClick={() => onFilterChange({ showOnlyFavorites: !filters.showOnlyFavorites })}
                  className={`filter-chip filter-chip-favorites ${filters.showOnlyFavorites ? 'active' : ''}`}
                >
                  <Star className={`w-4 h-4 ${filters.showOnlyFavorites ? 'fill-current' : ''}`} />
                  Show Only Favorites
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
