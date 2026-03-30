import { motion } from 'framer-motion'
import { Home, Wallet, Clock, Globe, TrendingUp } from 'lucide-react'
import { useStats } from '../hooks/useApartments'

const StatCard = ({ icon: Icon, label, value, subValue, delay, gradient, iconBg }) => (
  <motion.div
    className="glass-card rounded-2xl p-5 relative overflow-hidden group"
    initial={{ opacity: 0, y: 20, scale: 0.95 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    transition={{ delay, duration: 0.5, type: "spring", stiffness: 100 }}
    whileHover={{ y: -4, transition: { duration: 0.2 } }}
  >
    {/* Background gradient decoration */}
    <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full ${gradient} opacity-20 group-hover:opacity-30 transition-opacity`} />
    
    <div className="relative flex items-start justify-between">
      <div>
        <p className="text-gray-500 text-sm font-medium mb-1">{label}</p>
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        {subValue && (
          <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {subValue}
          </p>
        )}
      </div>
      <motion.div 
        className={`p-3 rounded-2xl ${iconBg}`}
        whileHover={{ rotate: 10, scale: 1.1 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        <Icon className="w-6 h-6 text-white" />
      </motion.div>
    </div>
  </motion.div>
)

const LoadingStat = ({ delay }) => (
  <motion.div 
    className="glass-card rounded-2xl p-5"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay }}
  >
    <div className="flex items-start justify-between">
      <div className="space-y-2">
        <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
        <div className="h-7 w-20 bg-gray-200 rounded animate-pulse" />
      </div>
      <div className="w-12 h-12 bg-gray-200 rounded-2xl animate-pulse" />
    </div>
  </motion.div>
)

export default function StatsCards() {
  const { stats, loading } = useStats()

  const formatPrice = (price) => {
    if (!price) return '¥0'
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      maximumFractionDigits: 0,
    }).format(price)
  }

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0, 0.1, 0.2, 0.3].map((delay, i) => <LoadingStat key={i} delay={delay} />)}
      </div>
    )
  }

  if (!stats) return null

  const statItems = [
    {
      icon: Home,
      label: 'Total Apartments',
      value: stats.total_apartments || 0,
      subValue: 'Available now',
      gradient: 'bg-gradient-to-br from-violet-400 to-violet-600',
      iconBg: 'bg-gradient-to-br from-violet-400 to-violet-600',
    },
    {
      icon: Wallet,
      label: 'Average Price',
      value: formatPrice(stats.avg_price),
      subValue: 'Per month',
      gradient: 'bg-gradient-to-br from-indigo-400 to-indigo-600',
      iconBg: 'bg-gradient-to-br from-indigo-400 to-indigo-600',
    },
    {
      icon: Clock,
      label: 'Best Commute',
      value: stats.best_commute ? `${stats.best_commute} min` : 'N/A',
      subValue: stats.best_commute ? 'Fastest route' : 'Calculate distances',
      gradient: 'bg-gradient-to-br from-blue-400 to-blue-600',
      iconBg: 'bg-gradient-to-br from-blue-400 to-blue-600',
    },
    {
      icon: Globe,
      label: 'Websites',
      value: stats.websites_count || 0,
      subValue: 'Sources tracked',
      gradient: 'bg-gradient-to-br from-emerald-400 to-emerald-600',
      iconBg: 'bg-gradient-to-br from-emerald-400 to-emerald-600',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statItems.map((item, index) => (
        <StatCard key={item.label} {...item} delay={index * 0.1} />
      ))}
    </div>
  )
}
