import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Home, Search, ArrowUpDown, Minimize2, AlertTriangle } from 'lucide-react'
import { useApartments, useTargets, useWebsites } from '../hooks/useApartments'
import FilterBar from './FilterBar'
import ApartmentCard from './ApartmentCard'
import ApartmentMap from './ApartmentMap'
import CustomDropdown from './CustomDropdown'
import { MAP_WARNING_THRESHOLD } from '../config/commuteThresholds'
import { useApartmentStore } from '../stores/apartmentStore'

// Custom loading component
const KawaiiLoader = () => (
  <motion.div 
    className="flex flex-col items-center justify-center py-16"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
  >
    <div className="loading-bounce mb-6">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <motion.p 
      className="text-gray-600 font-medium text-lg"
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity }}
    >
      Finding your dream home...
    </motion.p>
  </motion.div>
)

export default function Dashboard() {
  const { targets, loading: targetsLoading } = useTargets()
  const { websites, loading: websitesLoading } = useWebsites()
  const { apartments, loading, error, filters, updateFilters } = useApartments()
  const { favorites, seen } = useApartmentStore()
  const [selectedApartment, setSelectedApartment] = useState(null)
  const [selectionSource, setSelectionSource] = useState(null) // 'list' or 'map'
  const [sortBy, setSortBy] = useState('price')
  const [mapExpanded, setMapExpanded] = useState(false)

  // Handlers for selecting apartment from different sources
  const handleSelectFromList = useCallback((apt) => {
    setSelectionSource('list')
    setSelectedApartment(apt)
  }, [])

  const handleSelectFromMap = useCallback((apt) => {
    setSelectionSource('map')
    setSelectedApartment(apt)
  }, [])

  // Set initial targetId to first target when targets load
  useEffect(() => {
    if (targets.length > 0 && !filters.targetId) {
      updateFilters({ targetId: targets[0].id })
    }
  }, [targets, filters.targetId, updateFilters])

  // Set initial websites to first website when websites load
  useEffect(() => {
    if (websites.length > 0 && filters.websites === undefined) {
      updateFilters({ websites: [websites[0].name] })
    }
  }, [websites, filters.websites, updateFilters])

  // Prevent body scroll when map is expanded
  useEffect(() => {
    if (mapExpanded) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [mapExpanded])

  // Select first apartment by default when apartments load
  useEffect(() => {
    if (apartments.length > 0 && !selectedApartment) {
      setSelectedApartment(apartments[0])
    }
  }, [apartments, selectedApartment])

  // Filter apartments based on showSeen, showOnlySeen, and showOnlyFavorites
  const filteredApartments = useMemo(() => {
    return apartments.filter(apt => {
      // Filter by seen status (hide seen)
      if (filters.showSeen === false && seen[apt.id]) {
        return false
      }
      // Filter by seen status (show only seen)
      if (filters.showOnlySeen === true && !seen[apt.id]) {
        return false
      }
      // Filter by favorites
      if (filters.showOnlyFavorites === true && !favorites[apt.id]) {
        return false
      }
      return true
    })
  }, [apartments, filters.showSeen, filters.showOnlySeen, filters.showOnlyFavorites, favorites, seen])

  // Calculate price range for gradient coloring
  const priceRange = filteredApartments.length > 0 ? {
    min: Math.min(...filteredApartments.map(a => a.price)),
    max: Math.max(...filteredApartments.map(a => a.price))
  } : { min: 0, max: 0 }

  const sortedApartments = [...filteredApartments].sort((a, b) => {
    switch (sortBy) {
      case 'price':
        return a.price - b.price
      case 'price_desc':
        return b.price - a.price
      case 'distance':
        const aTime = a.distances?.[0]?.time_minutes || 999
        const bTime = b.distances?.[0]?.time_minutes || 999
        return aTime - bTime
      case 'value':
        const maxPrice = Math.max(...filteredApartments.map(apt => apt.price), 1)
        const maxTime = Math.max(...filteredApartments.flatMap(apt => apt.distances?.map(d => d.time_minutes) || [60]), 1)
        const aScore = (a.price / maxPrice) + ((a.distances?.[0]?.time_minutes || 60) / maxTime)
        const bScore = (b.price / maxPrice) + ((b.distances?.[0]?.time_minutes || 60) / maxTime)
        return aScore - bScore
      default:
        return 0
    }
  })

  if (error) {
    return (
      <motion.div
        className="glass-card rounded-2xl p-8 text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="text-6xl mb-4">😿</div>
        <h3 className="text-xl font-bold text-gray-700 mb-2">Oops! Something went wrong</h3>
        <p className="text-gray-500">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="btn-kawaii mt-4 px-6 py-2 rounded-full font-medium"
        >
          Try Again
        </button>
      </motion.div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters - hide when map is expanded to avoid duplicate */}
      {!mapExpanded && <FilterBar filters={filters} onFilterChange={updateFilters} />}
      
      {/* Warning when too many apartments - clustering is enabled */}
      {filteredApartments.length >= MAP_WARNING_THRESHOLD && (
        <motion.div
          className="bg-amber-50 border-2 border-amber-400 rounded-2xl p-4 flex items-center gap-4"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="p-2 bg-amber-100 rounded-xl">
            <AlertTriangle className="w-6 h-6 text-amber-600" />
          </div>
          <div className="flex-1">
            <h4 className="font-bold text-amber-800">Many apartments - Clustering enabled</h4>
            <p className="text-sm text-amber-700">
              Showing {filteredApartments.length} apartments. <strong>Marker clustering is active</strong> to improve performance. 
              Zoom in or use filters to see individual apartments.
            </p>
          </div>
        </motion.div>
      )}
      
      {/* Main Content */}
      {loading ? (
        <KawaiiLoader />
      ) : filteredApartments.length === 0 && !mapExpanded ? (
        <motion.div
          className="glass-card rounded-2xl p-12 text-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Home className="w-16 h-16 mx-auto text-violet-400 mb-4" />
          </motion.div>
          <h3 className="text-xl font-bold text-gray-700 mb-2">No apartments found</h3>
          <p className="text-gray-500 mb-4">
            Try adjusting your filters to discover more options!
          </p>
          <button 
            onClick={() => updateFilters({ minPrice: null, maxPrice: null, website: null, targetId: targets[0]?.id || null, maxTime: null })}
            className="btn-kawaii px-6 py-2 rounded-full font-medium"
          >
            Clear Filters
          </button>
        </motion.div>
      ) : (
        <>
          {/* Expanded Map Overlay */}
          <AnimatePresence>
            {mapExpanded && (
              <motion.div
                className="fixed inset-0 z-50 bg-slate-50/80 backdrop-blur-md flex flex-col"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {/* PERFECTLY CENTERED NOTCH (keep above overlays) */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 z-[300] w-full max-w-4xl pointer-events-auto">
                  <div className="bg-white shadow-xl border-x border-b border-slate-200 rounded-b-[2rem] px-0 py-0">
                    <FilterBar filters={filters} onFilterChange={updateFilters} />
                  </div>
                </div>
                
                {/* MAP CONTAINER WITH MARGINS */}
                <div className="flex-1 p-0 relative"> 
                  {/* rounded-[2rem] */}
                  <div className="w-full h-full overflow-hidden relative">
                    {/* Gray overlay when no apartments found (does not block filter bar) */}
                    {filteredApartments.length === 0 && (
                      <motion.div
                        className="absolute inset-0 z-40 bg-gray-900/40 backdrop-blur-[2px] pointer-events-none"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        style={{ filter: 'grayscale(0.7)' }}
                      />
                    )}
                    
                    {/* No apartments banner - centered on screen */}
                    {filteredApartments.length === 0 && (
                      <motion.div
                        className="absolute inset-0 z-[200] flex items-center justify-center"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                      >
                        <div className="bg-white shadow-2xl border-4 border-red-500 rounded-2xl px-10 py-6 max-w-lg flex items-center gap-4">
                          <div className="text-5xl">🔍</div>
                          <div>
                            <h3 className="font-bold text-gray-900 text-xl mb-1">No apartments found</h3>
                            <p className="text-sm text-gray-600">Try adjusting your filters above</p>
                          </div>
                        </div>
                      </motion.div>
                    )}
                    <ApartmentMap
                      apartments={sortedApartments}
                      selectedApartment={selectedApartment}
                      selectionSource={selectionSource}
                      onSelect={handleSelectFromMap}
                      selectedTargetId={filters.targetId}
                      priceRange={priceRange}
                      fullHeight
                      openPopupOnSelect
                      showEmptyState={filteredApartments.length === 0}
                    />
                    
                    {/* MINIMIZE BUTTON - POSITIONED OVER THE MAP */}
                    <button
                      onClick={() => setMapExpanded(false)}
                      className="absolute top-20 right-4 z-[1002] bg-white/95 backdrop-blur-sm rounded-2xl p-3 shadow-2xl border-2 border-slate-300 hover:scale-110 hover:border-violet-400 transition-all"
                    >
                      <Minimize2 className="w-6 h-6 text-slate-700" />
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="glass-card rounded-2xl p-4 max-w-[2000px] mx-auto">
            <div className="flex gap-4 h-[calc(100vh-280px)] min-h-[500px]">
            {/* Map */}
            {!mapExpanded && (
              <motion.div 
                className="relative flex-1"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="map-container-split h-full">
                  <ApartmentMap
                    apartments={sortedApartments}
                    selectedApartment={selectedApartment}
                    selectionSource={selectionSource}
                    onSelect={handleSelectFromMap}
                    onExpandToggle={() => setMapExpanded(true)}
                    selectedTargetId={filters.targetId}
                    priceRange={priceRange}
                    fullHeight
                    openPopupOnSelect
                  />
                </div>
              </motion.div>
            )}
            
            {/* Apartment List */}
            {/* Results Header */}
            <div className="flex-1 flex flex-col">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2">
                  {/* <Search className="w-4 h-4 text-violet-400" />
                  <p className="text-gray-700 text-sm">
                    <span className="font-bold gradient-text">{apartments.length}</span> apartments found
                  </p> */}
                </div>
                
                {/* Sort Dropdown */}
                <CustomDropdown
                  value={sortBy}
                  onChange={setSortBy}
                  icon={ArrowUpDown}
                  options={[
                    { value: 'price', label: 'Price: Low to High' },
                    { value: 'price_desc', label: 'Price: High to Low' },
                    { value: 'distance', label: 'Shortest Commute' },
                    { value: 'value', label: 'Best Value' },
                  ]}
                  className="min-w-[180px]"
                />
              </div>
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="flex-1 flex flex-col min-h-0"
              >
                <div className="apartment-list-wrapper flex-1 overflow-hidden">
                  <div className="space-y-3 apartment-list pt-4 pb-4 h-full overflow-y-auto">
                    {sortedApartments.map((apt, index) => (
                      <ApartmentCard
                        key={apt.id}
                        apartment={apt}
                        index={index}
                        onSelect={handleSelectFromList}
                        isSelected={selectedApartment?.id === apt.id}
                        priceRange={priceRange}
                      />
                    ))}
                  </div>
                </div>
                
                {/* Load more hint */}
                {sortedApartments.length >= 20 && (
                  <motion.div 
                    className="text-center py-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    <p className="text-gray-400 text-sm">
                      Showing top {sortedApartments.length} results
                    </p>
                  </motion.div>
                )}
              </motion.div>
              </div>
            </div>
            </div>
        </>
      )}
    </div>
  )
}
