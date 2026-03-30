import { useEffect, useRef, memo, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import { MapPin, Navigation, ExternalLink, Maximize2, Footprints, Bike, Train, Star, Eye, EyeOff } from 'lucide-react'
import { useTargets } from '../hooks/useApartments'
import { COMMUTE_THRESHOLDS, MAP_WARNING_THRESHOLD } from '../config/commuteThresholds'
import { useApartmentStore } from '../stores/apartmentStore'

// Icon cache to prevent recreating icons on every render
const iconCache = new Map()

// Custom marker icons based on commute time with better styling
const createIcon = (color, isSelected = false, isSeen = false, isFavorite = false) => {
  const cacheKey = `${color}-${isSelected}-${isSeen}-${isFavorite}`
  if (iconCache.has(cacheKey)) {
    return iconCache.get(cacheKey)
  }

  const size = isSelected ? 40 : 32
  const shadow = isSelected ? '0 0 20px rgba(139,92,246,0.4)' : '0 4px 15px rgba(0,0,0,0.15)'
  const iconSize = isSelected ? 18 : 14
  
  // Border styling: favorites get animated class (priority over seen), seen get black, default is white
  let borderStyle = 'border: 3px solid white;'
  let extraClass = ''
  if (isFavorite) {
    borderStyle = 'border: 3px solid #8b5cf6;'  // Initial color, animation will override
    extraClass = 'favorite-marker-border'
  } else if (isSeen) {
    borderStyle = 'border: 3px solid #1f2937;'  // Black border for seen
  }
  
  // Create Home icon SVG
  const homeIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${iconSize}" height="${iconSize}" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`
  
  const icon = L.divIcon({
    className: 'custom-marker',
    html: `
      <div class="${extraClass}" style="
        background: linear-gradient(135deg, ${color}, ${color}dd);
        width: ${size}px;
        height: ${size}px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        ${borderStyle}
        box-shadow: ${shadow};
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          transform: rotate(45deg);
          display: flex;
          align-items: center;
          justify-content: center;
        ">${homeIconSvg}</div>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size/2, size],
    popupAnchor: [0, -size],
  })
  
  iconCache.set(cacheKey, icon)
  return icon
}

// Commute category constants
const COMMUTE_CATEGORIES = {
  GREEN: 'green',
  AMBER: 'amber', 
  RED: 'red',
  VIOLET: 'violet'
}

const CATEGORY_COLORS = {
  [COMMUTE_CATEGORIES.GREEN]: '#10b981',
  [COMMUTE_CATEGORIES.AMBER]: '#f59e0b',
  [COMMUTE_CATEGORIES.RED]: '#ef4444',
  [COMMUTE_CATEGORIES.VIOLET]: '#8b5cf6'
}

// Get commute category for an apartment
const getCommuteCategory = (apartment) => {
  if (!apartment.distances || apartment.distances.length === 0) {
    return COMMUTE_CATEGORIES.VIOLET
  }
  const bestTime = Math.min(...apartment.distances.map(d => d.time_minutes))
  if (bestTime <= COMMUTE_THRESHOLDS.greenMax) return COMMUTE_CATEGORIES.GREEN
  if (bestTime <= COMMUTE_THRESHOLDS.orangeMax) return COMMUTE_CATEGORIES.AMBER
  return COMMUTE_CATEGORIES.RED
}

// Get color based on commute time
const getCommuteColor = (apartment) => {
  return CATEGORY_COLORS[getCommuteCategory(apartment)]
}

const getMarkerIcon = (apartment, isSelected, isSeen = false, isFavorite = false) => {
  const color = getCommuteColor(apartment)
  return createIcon(color, isSelected, isSeen, isFavorite)
}

// Create custom cluster icon for a specific color category
const createClusterIcon = (cluster, color) => {
  const count = cluster.getChildCount()
  
  let size = 'small'
  let dimensions = 40
  
  if (count >= 100) {
    size = 'large'
    dimensions = 50
  } else if (count >= 10) {
    size = 'medium'
    dimensions = 45
  }
  
  return L.divIcon({
    html: `<div style="
      background-color: ${color};
      width: ${dimensions}px;
      height: ${dimensions}px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: ${size === 'large' ? '14px' : size === 'medium' ? '13px' : '12px'};
      border: 3px solid white;
    ">${count}</div>`,
    className: `marker-cluster marker-cluster-${size}`,
    iconSize: L.point(dimensions, dimensions)
  })
}

// Target/destination marker icon (cached)
let cachedTargetIcon = null
const createTargetIcon = () => {
  if (cachedTargetIcon) return cachedTargetIcon
  
  // Crosshair SVG icon
  const crosshairSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/></svg>`
  
  cachedTargetIcon = L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        width: 44px;
        height: 44px;
        border-radius: 50%;
        border: 4px solid white;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        ${crosshairSvg}
      </div>
    `,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
    popupAnchor: [0, -22],
  })
  return cachedTargetIcon
}

// Component to update map center dynamically without remounting
function MapUpdater({ center }) {
  const map = useMap()
  const prevCenterRef = useRef(null)
  const initializedRef = useRef(false)
  
  useEffect(() => {
    if (center && center[0] && center[1]) {
      // Only update if center actually changed (compare values, not reference)
      const prevCenter = prevCenterRef.current
      if (prevCenter && prevCenter[0] === center[0] && prevCenter[1] === center[1]) {
        return
      }
      // Skip setView if map is already at this center (prevents teleport on re-render)
      if (initializedRef.current) {
        const currentCenter = map.getCenter()
        const distance = Math.abs(currentCenter.lat - center[0]) + Math.abs(currentCenter.lng - center[1])
        if (distance < 0.0001) {
          prevCenterRef.current = center
          return
        }
      }
      prevCenterRef.current = center
      initializedRef.current = true
      map.setView(center, map.getZoom(), { animate: false })
    }
  }, [center, map])
  
  return null
}

// Component to fly to selected apartment and open its popup
// Map click: short animation from current view → centered apt
// List click: animation from old apt → centered new apt  
function FlyToMarker({ apartment, markerRefs, openPopupOnSelect, selectionSource }) {
  const map = useMap()
  const prevApartmentIdRef = useRef(null)
  
  useEffect(() => {
    if (!apartment?.address?.latitude || !apartment?.address?.longitude) {
      return
    }
    
    // Only fly if apartment ID actually changed
    // This prevents unwanted movement when clicking favorite/seen buttons
    if (prevApartmentIdRef.current === apartment.id) {
      return
    }
    prevApartmentIdRef.current = apartment.id
    
    // Use zoom 18 to ensure markers are fully unclustered (matches disableClusteringAtZoom)
    const targetZoom = 18
    
    // Offset the center northward so the marker appears lower on screen, leaving room for popup above
    // At zoom 18, ~0.0005 degrees latitude ≈ 50-60 pixels offset
    const latOffset = 0.0005
    const targetPos = [apartment.address.latitude + latOffset, apartment.address.longitude]
    
    // Both sources animate to the apt, but with different feel
    // Map click: shorter/snappier (user clicked nearby)
    // List click: longer animation (might be far away)
    const duration = selectionSource === 'map' ? 0.4 : 0.8
    
    map.flyTo(targetPos, targetZoom, { duration })
    
    // Open popup after animation - with retry for clustered markers
    if (openPopupOnSelect && markerRefs?.current) {
      map.closePopup()
      
      // Try to open popup multiple times as cluster may take time to uncluster
      const tryOpenPopup = (attempts = 0) => {
        const markerRef = markerRefs.current[apartment.id]
        if (markerRef) {
          try {
            markerRef.openPopup()
          } catch (e) {
            // Marker might still be in cluster, retry
            if (attempts < 5) {
              setTimeout(() => tryOpenPopup(attempts + 1), 150)
            }
          }
        } else if (attempts < 5) {
          // Marker ref not available yet, retry
          setTimeout(() => tryOpenPopup(attempts + 1), 150)
        }
      }
      
      // Initial delay for fly animation to complete + cluster to uncluster
      const delay = duration * 1000 + 200
      setTimeout(() => tryOpenPopup(0), delay)
    }
  }, [apartment?.id, map, markerRefs, openPopupOnSelect, selectionSource])
  
  return null
}

// Simple marker renderer - not memoized since markerRef breaks it anyway
// Performance comes from simplified rendering, not memoization
function ApartmentMarker({ apt, isSelected, onSelect, markerRefs, priceRange }) {
  const { favorites, seen, toggleFavorite, toggleSeen } = useApartmentStore()
  const isFavorite = !!favorites[apt.id]
  const isSeen = !!seen[apt.id]
  const icon = getMarkerIcon(apt, isSelected, isSeen, isFavorite)
  const position = [apt.address.latitude, apt.address.longitude]

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      maximumFractionDigits: 0,
    }).format(price)
  }

  const getPriceColor = (price) => {
    if (!priceRange || priceRange.min === priceRange.max) return '#8b5cf6'
    const ratio = (price - priceRange.min) / (priceRange.max - priceRange.min)
    if (ratio <= 0.5) {
      const r = Math.round(34 + (ratio * 2) * (234 - 34))
      const g = Math.round(197 + (ratio * 2) * (179 - 197))
      const b = Math.round(94 + (ratio * 2) * (8 - 94))
      return `rgb(${r}, ${g}, ${b})`
    } else {
      const adjustedRatio = (ratio - 0.5) * 2
      const r = Math.round(234 + adjustedRatio * (239 - 234))
      const g = Math.round(179 - adjustedRatio * (179 - 68))
      const b = Math.round(8 + adjustedRatio * (68 - 8))
      return `rgb(${r}, ${g}, ${b})`
    }
  }

  return (
    <Marker
      position={position}
      icon={icon}
      ref={(ref) => { if (ref) markerRefs.current[apt.id] = ref }}
      eventHandlers={{ click: () => onSelect(apt) }}
    >
      <Popup autoPan={false} closeOnClick={false} keepInView={false}>
        <div className="p-1 min-w-[200px]" onClick={(e) => e.stopPropagation()}>
          {apt.image_url && (
            <div className="mb-2 -mx-1 -mt-1 rounded-t-lg overflow-hidden bg-gray-100 relative" style={{ minHeight: '120px' }}>
              <img 
                src={apt.image_url} 
                alt={apt.name}
                className="w-full max-h-40 object-contain"
                loading="eager"
                onError={(e) => { e.target.parentElement.style.display = 'none' }}
              />
              {/* Favorite Star - Top Right of Image */}
              <button
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  e.nativeEvent.stopImmediatePropagation()
                  toggleFavorite(apt.id)
                }}
                className={`absolute top-2 right-2 p-1.5 rounded-full transition-all hover:scale-110 ${
                  isFavorite 
                    ? 'bg-amber-400 text-white shadow-lg' 
                    : 'bg-white/80 text-gray-400 hover:bg-amber-100 hover:text-amber-500'
                }`}
                title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
              >
                <Star className={`w-5 h-5 ${isFavorite ? 'fill-current' : ''}`} />
              </button>
            </div>
          )}
          
          <h3 className="font-bold text-sm mb-2 line-clamp-2 text-gray-800">
            {apt.name}
          </h3>
          
          <div className="flex items-center justify-between mb-2">
            <span 
              className="font-bold text-base px-2 py-0.5 rounded-lg text-white"
              style={{ backgroundColor: getPriceColor(apt.price) }}
            >
              {formatPrice(apt.price)}
            </span>
            <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
              {apt.website_name}
            </span>
          </div>
          
          <p className="text-xs text-gray-500 mb-2 flex items-start gap-1">
            <MapPin className="w-3 h-3 shrink-0 mt-0.5" />
            <span className="line-clamp-2">{apt.address.address_text}</span>
          </p>
          
          {apt.distances && apt.distances.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-xs bg-gray-50 rounded-lg p-2 mb-2">
              {apt.distances[0].time_transit_walk_minutes && (
                <span className="flex items-center gap-1 text-blue-600" title="Walk + Train">
                  <Footprints className="w-3 h-3" />
                  <Train className="w-3 h-3" />
                  {apt.distances[0].time_transit_walk_minutes}m
                </span>
              )}
              {apt.distances[0].time_transit_bike_minutes && (
                <span className="flex items-center gap-1 text-purple-600" title="Bike + Train">
                  <Bike className="w-3 h-3" />
                  <Train className="w-3 h-3" />
                  {apt.distances[0].time_transit_bike_minutes}m
                </span>
              )}
              {apt.distances[0].time_bike_minutes && (
                <span className="flex items-center gap-1 text-emerald-600" title="Cycling only">
                  <Bike className="w-3 h-3" />
                  {apt.distances[0].time_bike_minutes}m
                </span>
              )}
            </div>
          )}
          
          <div className="flex gap-1.5 mt-1">
            {apt.url && (
              <a
                href={apt.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-kawaii flex-1 flex items-center justify-center gap-1.5 text-xs rounded-lg py-2 no-underline"
                style={{ color: 'white', textDecoration: 'none' }}
              >
                <ExternalLink className="w-3 h-3" />
                View Listing
              </a>
            )}
            
            {/* Seen Status Button */}
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                e.nativeEvent.stopImmediatePropagation()
                toggleSeen(apt.id)
              }}
              className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1 transition-all ${
                isSeen
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={isSeen ? 'Mark as unseen' : 'Mark as seen'}
            >
              {isSeen ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              {isSeen ? 'Seen' : 'Mark'}
            </button>
          </div>
        </div>
      </Popup>
    </Marker>
  )
}

// Default center (Tokyo - Toyosu area)
const DEFAULT_CENTER = [35.6462, 139.7908]

function ApartmentMap({ apartments, selectedApartment, selectionSource, onSelect, onExpandToggle, fullHeight = false, selectedTargetId = null, priceRange = null, openPopupOnSelect = false, showEmptyState = false }) {
  const { targets } = useTargets()
  const markerRefs = useRef({})
  
  // Memoize filtered apartments with coordinates
  const mappableApartments = useMemo(() => 
    apartments.filter(apt => apt.address?.latitude && apt.address?.longitude),
    [apartments]
  )
  
  // Group apartments by commute category for color-based clustering
  const apartmentsByCategory = useMemo(() => {
    const groups = {
      [COMMUTE_CATEGORIES.GREEN]: [],
      [COMMUTE_CATEGORIES.AMBER]: [],
      [COMMUTE_CATEGORIES.RED]: [],
      [COMMUTE_CATEGORIES.VIOLET]: []
    }
    mappableApartments.forEach(apt => {
      const category = getCommuteCategory(apt)
      groups[category].push(apt)
    })
    return groups
  }, [mappableApartments])

  // Memoize destination lookup
  const destination = useMemo(() => 
    selectedTargetId 
      ? targets?.find(t => t.id === selectedTargetId && t.latitude && t.longitude)
      : targets?.find(t => t.latitude && t.longitude),
    [selectedTargetId, targets]
  )

  // Memoize center calculation
  const center = useMemo(() => {
    if (destination) {
      return [destination.latitude, destination.longitude]
    }
    if (mappableApartments.length > 0) {
      const latSum = mappableApartments.reduce((sum, a) => sum + a.address.latitude, 0)
      const lngSum = mappableApartments.reduce((sum, a) => sum + a.address.longitude, 0)
      return [latSum / mappableApartments.length, lngSum / mappableApartments.length]
    }
    return DEFAULT_CENTER
  }, [destination, mappableApartments])

  // Memoize the selected apartment ID for comparison
  const selectedApartmentId = selectedApartment?.id

  return (
    <div
      className={`glass-card rounded-2xl overflow-hidden ${fullHeight ? 'h-full' : ''}`}
    >
      {/* Map Header */}
      <div className="p-3 flex items-center justify-between border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-gradient-to-br from-violet-400 to-indigo-500 rounded-lg">
            <Navigation className="w-4 h-4 text-white" />
          </div>
          <span className="font-medium text-gray-700 text-sm">
            {mappableApartments.length} locations
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Legend */}
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-gray-500 hidden sm:inline">≤{COMMUTE_THRESHOLDS.greenMax}m</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span className="text-gray-500 hidden sm:inline">{COMMUTE_THRESHOLDS.greenMax}-{COMMUTE_THRESHOLDS.orangeMax}m</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              <span className="text-gray-500 hidden sm:inline">&gt;{COMMUTE_THRESHOLDS.orangeMax}m</span>
            </span>
          </div>
        </div>
      </div>
      
      {/* Map Container */}
      <div className={fullHeight ? 'p-2 h-[calc(100%-56px)] relative' : 'p-2 relative'}>
        {/* Expand Button - Positioned over the map */}
        {onExpandToggle && (
          <button
            onClick={onExpandToggle}
            className="absolute top-4 right-4 z-[1000] p-2.5 bg-white/95 backdrop-blur-sm rounded-xl border-2 border-slate-300 hover:border-violet-400 hover:scale-110 transition-all shadow-lg"
            title="Expand map"
          >
            <Maximize2 className="w-5 h-5 text-gray-700" />
          </button>
        )}
        <MapContainer
          center={center}
          zoom={12}
          style={{ height: fullHeight ? '100%' : '400px', width: '100%', borderRadius: '1rem' }}
          scrollWheelZoom={true}
          attributionControl={false}
          preferCanvas={true}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapUpdater center={center} />
          
          {/* Destination Marker */}
          {destination && (
            <Marker
              position={[destination.latitude, destination.longitude]}
              icon={createTargetIcon()}
            >
              <Popup>
                <div className="p-2 text-center">
                  <h3 className="font-bold text-blue-600 mb-1">{destination.name}</h3>
                  <p className="text-xs text-gray-500">{destination.address}</p>
                  <p className="text-xs text-blue-500 mt-1">🎯 Your destination</p>
                </div>
              </Popup>
            </Marker>
          )}
          
          {/* Use color-based clustering when there are many apartments */}
          {mappableApartments.length >= MAP_WARNING_THRESHOLD ? (
            // Cluster mode - group by color category with MIN_CLUSTER_SIZE check in iconCreateFunction
            Object.entries(apartmentsByCategory).map(([category, apts]) => {
              if (apts.length === 0) return null
              
              const color = CATEGORY_COLORS[category]
              
              return (
                <MarkerClusterGroup
                  key={category}
                  chunkedLoading
                  maxClusterRadius={50}
                  spiderfyOnMaxZoom={true}
                  showCoverageOnHover={false}
                  zoomToBoundsOnClick={true}
                  disableClusteringAtZoom={18}
                  iconCreateFunction={(cluster) => createClusterIcon(cluster, color)}
                >
                  {apts.map((apt) => (
                    <ApartmentMarker
                      key={apt.id}
                      apt={apt}
                      isSelected={selectedApartmentId === apt.id}
                      onSelect={onSelect}
                      markerRefs={markerRefs}
                      priceRange={priceRange}
                    />
                  ))}
                </MarkerClusterGroup>
              )
            })
          ) : (
            // No clustering - render all markers directly
            mappableApartments.map((apt) => (
              <ApartmentMarker
                key={apt.id}
                apt={apt}
                isSelected={selectedApartmentId === apt.id}
                onSelect={onSelect}
                markerRefs={markerRefs}
                priceRange={priceRange}
              />
            ))
          )}
          
          <FlyToMarker apartment={selectedApartment} markerRefs={markerRefs} openPopupOnSelect={openPopupOnSelect} selectionSource={selectionSource} />
        </MapContainer>
      </div>
    </div>
  )
}

// Export memoized version to prevent unnecessary re-renders
export default memo(ApartmentMap)
