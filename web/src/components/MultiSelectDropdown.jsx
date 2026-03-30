import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'

export default function MultiSelectDropdown({ 
  options, 
  selectedValues = [], 
  onChange, 
  placeholder = 'Select...',
  icon: Icon,
  className = ''
}) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleToggle = (value) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter(v => v !== value))
    } else {
      onChange([...selectedValues, value])
    }
  }

  const handleSelectAll = () => {
    onChange(options.map(o => o.value))
  }

  const handleDeselectAll = () => {
    onChange([])
  }

  const getDisplayText = () => {
    if (selectedValues.length === 0) return placeholder
    if (selectedValues.length === options.length) return 'All selected'
    if (selectedValues.length === 1) {
      const option = options.find(o => o.value === selectedValues[0])
      return option?.label || selectedValues[0]
    }
    return `${selectedValues.length} selected`
  }

  const allSelected = selectedValues.length === options.length && options.length > 0

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 bg-white/50 border-2 border-gray-100 rounded-xl text-sm transition-all hover:border-violet-200 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/15 focus:outline-none"
      >
        <div className="flex items-center gap-2 min-w-0">
          {Icon && <Icon className="w-4 h-4 text-gray-400 shrink-0" />}
          <span className={`truncate ${selectedValues.length > 0 ? 'text-gray-700' : 'text-gray-400'}`}>
            {getDisplayText()}
          </span>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 right-0 mt-1 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden z-[100]"
            style={{ boxShadow: '0 10px 40px rgba(100, 116, 139, 0.15)' }}
          >
            <div className="max-h-60 overflow-y-auto py-1">
              {/* Select All / Deselect All option */}
              <button
                type="button"
                onClick={allSelected ? handleDeselectAll : handleSelectAll}
                className={`w-full text-left px-3 py-2.5 text-sm transition-all ${
                  allSelected
                    ? 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white'
                    : 'text-gray-600 hover:bg-slate-50 hover:text-violet-600'
                }`}
              >
                {allSelected ? 'Deselect All' : 'Select All'}
              </button>
              
              <div className="h-px bg-gray-100 my-1" />
              
              {/* Individual options */}
              {options.map((option) => {
                const isSelected = selectedValues.includes(option.value)
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleToggle(option.value)}
                    className={`w-full text-left px-3 py-2.5 text-sm transition-all ${
                      isSelected
                        ? 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white'
                        : 'text-gray-600 hover:bg-slate-50 hover:text-violet-600'
                    }`}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
