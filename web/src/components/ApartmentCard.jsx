import { MapPin, Train, Bike, ExternalLink, Clock, Sparkles, Footprints, Star, Eye, EyeOff } from 'lucide-react'
import { COMMUTE_THRESHOLDS } from '../config/commuteThresholds'
import { useApartmentStore } from '../stores/apartmentStore'

export default function ApartmentCard({ apartment, index, onSelect, isSelected, priceRange }) {
  const { favorites, seen, toggleFavorite, toggleSeen } = useApartmentStore()
  const isFavorite = !!favorites[apartment.id]
  const isSeen = !!seen[apartment.id]

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      maximumFractionDigits: 0,
    }).format(price)
  }

  // Calculate price gradient color (green = cheap, orange = mid, red = expensive)
  const getPriceColor = () => {
    if (!priceRange || priceRange.min === priceRange.max) return '#8b5cf6' // fallback violet
    const ratio = (apartment.price - priceRange.min) / (priceRange.max - priceRange.min)
    // Green (cheap) -> Yellow (mid) -> Red (expensive)
    if (ratio <= 0.5) {
      // Green to Yellow
      const r = Math.round(34 + (ratio * 2) * (234 - 34))
      const g = Math.round(197 + (ratio * 2) * (179 - 197))
      const b = Math.round(94 + (ratio * 2) * (8 - 94))
      return `rgb(${r}, ${g}, ${b})`
    } else {
      // Yellow to Red
      const adjustedRatio = (ratio - 0.5) * 2
      const r = Math.round(234 + adjustedRatio * (239 - 234))
      const g = Math.round(179 - adjustedRatio * (179 - 68))
      const b = Math.round(8 + adjustedRatio * (68 - 8))
      return `rgb(${r}, ${g}, ${b})`
    }
  }

  const getBestCommute = () => {
    if (!apartment.distances || apartment.distances.length === 0) return null
    return apartment.distances.reduce((best, d) => 
      !best || d.time_minutes < best.time_minutes ? d : best
    , null)
  }

  const bestCommute = getBestCommute()

  const getCommuteStyle = (minutes) => {
    if (minutes <= COMMUTE_THRESHOLDS.greenMax) return { bg: 'bg-emerald-500', text: 'Excellent', emoji: '✨' }
    if (minutes <= COMMUTE_THRESHOLDS.orangeMax) return { bg: 'bg-amber-500', text: 'Good', emoji: '👍' }
    return { bg: 'bg-rose-500', text: 'Far', emoji: '🚅' }
  }

  const commuteStyle = bestCommute ? getCommuteStyle(bestCommute.time_minutes) : null

  return (
    <div
      className={`glass-card rounded-2xl cursor-pointer kawaii-card transition-all duration-200 ${
        isSelected ? 'selected ring-2 ring-violet-400 shadow-lg' : 'hover:shadow-md'
      }`}
      onClick={() => onSelect(apartment)}
    >
      <div className="p-5">
        {/* Header with Price and Favorite Star */}
        <div className="flex justify-between items-start gap-2 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-gray-800 line-clamp-2 leading-tight mb-1">
              {apartment.name}
            </h3>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded-lg font-medium">
                {apartment.website_name}
              </span>
              {bestCommute && (
                <span className={`text-xs px-2 py-1 ${commuteStyle.bg} text-white rounded-lg font-medium flex items-center gap-1`}>
                  <Clock className="w-3 h-3" />
                  {bestCommute.time_minutes} min
                </span>
              )}
            </div>
          </div>
          
          {/* Price Badge */}
          <div 
            className="text-lg whitespace-nowrap font-bold px-3 py-1.5 rounded-xl text-white shadow-sm h-[38px] flex items-center"
            style={{ backgroundColor: getPriceColor() }}
          >
            {formatPrice(apartment.price)}
          </div>
          
          {/* Favorite Star - same height as price badge */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              e.nativeEvent.stopImmediatePropagation()
              toggleFavorite(apartment.id)
            }}
            className={`h-[38px] w-[38px] rounded-xl transition-all hover:scale-110 flex items-center justify-center ${
              isFavorite 
                ? 'bg-amber-100 text-amber-500' 
                : 'bg-gray-100 text-gray-400 hover:bg-amber-50 hover:text-amber-400'
            }`}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star className={`w-5 h-5 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
        </div>

        {/* Address */}
        {apartment.address && (
          <div className="flex items-start gap-2 mb-3 text-sm text-gray-600">
            <MapPin className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
            <span className="line-clamp-2">{apartment.address.address_text}</span>
          </div>
        )}

        {/* Commute Details */}
        {bestCommute && (
          <div className="bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl p-3 mb-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                To: {bestCommute.target_name}
              </p>
              <span className="text-xs text-gray-400">
                {commuteStyle.emoji} {commuteStyle.text}
              </span>
            </div>
            <div className="flex flex-wrap gap-3">
              {/* Walk + Transit */}
              {bestCommute.time_transit_walk_minutes && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="p-1.5 bg-blue-100 rounded-lg flex items-center gap-0.5">
                    <Footprints className="w-3 h-3 text-blue-400" />
                    <Train className="w-4 h-4 text-blue-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-700">{bestCommute.time_transit_walk_minutes} min</p>
                    <p className="text-xs text-gray-400">Walk+Train</p>
                  </div>
                </div>
              )}
              {/* Bike + Transit */}
              {bestCommute.time_transit_bike_minutes && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="p-1.5 bg-purple-100 rounded-lg flex items-center gap-0.5">
                    <Bike className="w-3 h-3 text-purple-400" />
                    <Train className="w-4 h-4 text-purple-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-700">{bestCommute.time_transit_bike_minutes} min</p>
                    <p className="text-xs text-gray-400">Bike+Train</p>
                  </div>
                </div>
              )}
              {/* Bike Only */}
              {bestCommute.time_bike_minutes && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="p-1.5 bg-emerald-100 rounded-lg">
                    <Bike className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-700">{bestCommute.time_bike_minutes} min</p>
                    <p className="text-xs text-gray-400">Cycling</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          {apartment.url && (
            <a
              href={apartment.url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-kawaii flex-1 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-[0.98] transition-transform"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="w-4 h-4" />
              View Listing
            </a>
          )}
          
          {/* Seen Status Button */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              e.nativeEvent.stopImmediatePropagation()
              toggleSeen(apartment.id)
            }}
            className={`px-4 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] ${
              isSeen
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title={isSeen ? 'Mark as unseen' : 'Mark as seen'}
          >
            {isSeen ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {isSeen ? 'Seen' : 'Mark Seen'}
          </button>
        </div>
      </div>
    </div>
  )
}
