import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const STORAGE_KEY = 'apt-finder-user-data'

/**
 * LocalStorage Manager for apartment favorites and seen status.
 * 
 * Data structure:
 * {
 *   favorites: Set<number>,  // apartment IDs
 *   seen: Set<number>        // apartment IDs
 * }
 * 
 * Stored as arrays in localStorage for JSON compatibility,
 * converted to Sets in memory for O(1) lookups.
 */
export const useApartmentStore = create(
  persist(
    (set, get) => ({
      // State - using objects for fast lookups (converted from arrays in storage)
      favorites: {},  // { [aptId]: true }
      seen: {},       // { [aptId]: true }

      // Toggle favorite status for an apartment
      toggleFavorite: (aptId) => {
        set((state) => {
          const newFavorites = { ...state.favorites }
          if (newFavorites[aptId]) {
            delete newFavorites[aptId]
          } else {
            newFavorites[aptId] = true
          }
          return { favorites: newFavorites }
        })
      },

      // Toggle seen status for an apartment
      toggleSeen: (aptId) => {
        set((state) => {
          const newSeen = { ...state.seen }
          if (newSeen[aptId]) {
            delete newSeen[aptId]
          } else {
            newSeen[aptId] = true
          }
          return { seen: newSeen }
        })
      },

      // Check if apartment is favorite
      isFavorite: (aptId) => {
        return !!get().favorites[aptId]
      },

      // Check if apartment is seen
      isSeen: (aptId) => {
        return !!get().seen[aptId]
      },

      // Get all favorite IDs
      getFavoriteIds: () => {
        return Object.keys(get().favorites).map(Number)
      },

      // Get all seen IDs
      getSeenIds: () => {
        return Object.keys(get().seen).map(Number)
      },

      // Clear all favorites
      clearFavorites: () => {
        set({ favorites: {} })
      },

      // Clear all seen
      clearSeen: () => {
        set({ seen: {} })
      },

      // Clear all data
      clearAll: () => {
        set({ favorites: {}, seen: {} })
      },

      // Get counts
      getFavoritesCount: () => {
        return Object.keys(get().favorites).length
      },

      getSeenCount: () => {
        return Object.keys(get().seen).length
      },
    }),
    {
      name: STORAGE_KEY,
      // Custom storage serialization for optimized storage
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name)
          if (!str) return null
          
          try {
            const data = JSON.parse(str)
            // Convert arrays back to objects for fast lookups
            return {
              state: {
                favorites: arrayToObject(data.state?.favorites || []),
                seen: arrayToObject(data.state?.seen || []),
              },
              version: data.version,
            }
          } catch {
            return null
          }
        },
        setItem: (name, value) => {
          // Convert objects to arrays for compact storage
          const data = {
            state: {
              favorites: Object.keys(value.state.favorites).map(Number),
              seen: Object.keys(value.state.seen).map(Number),
            },
            version: value.version,
          }
          localStorage.setItem(name, JSON.stringify(data))
        },
        removeItem: (name) => {
          localStorage.removeItem(name)
        },
      },
    }
  )
)

// Helper function to convert array to object
function arrayToObject(arr) {
  const obj = {}
  for (const id of arr) {
    obj[id] = true
  }
  return obj
}

// Export individual selectors for optimized re-renders
export const useFavorites = () => useApartmentStore((state) => state.favorites)
export const useSeen = () => useApartmentStore((state) => state.seen)
export const useToggleFavorite = () => useApartmentStore((state) => state.toggleFavorite)
export const useToggleSeen = () => useApartmentStore((state) => state.toggleSeen)
