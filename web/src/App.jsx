import { motion } from 'framer-motion'
import Dashboard from './components/Dashboard'
import { Home, Heart } from 'lucide-react'
import StatsCards from './components/StatsCards'

function App() {
  return (
    <div className="min-h-screen">
      {/* Animated background elements - subtle and neutral */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute top-20 left-10 w-64 h-64 bg-violet-200 rounded-full mix-blend-multiply filter blur-3xl opacity-15 animate-float" />
        <div className="absolute top-40 right-10 w-72 h-72 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-15 animate-float" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-20 left-1/3 w-80 h-80 bg-slate-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" style={{ animationDelay: '2s' }} />
      </div>

      {/* Combined Header + Stats Block */}
      <motion.header 
        className="relative z-10 py-6"
        initial={{ y: -30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <div className="container mx-auto px-4">
          <div className="header-block rounded-3xl p-6">
            {/* Title */}
            <div className="text-center mb-6">
              <motion.div
                className="flex items-center justify-center gap-3 mb-1"
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              >
                <Home className="w-8 h-8 text-violet-500" />
                <h1 className="text-3xl md:text-5xl font-bold gradient-text">
                  APT-Finder
                </h1>
              </motion.div>
              {/* <motion.p 
                className="text-gray-500 text-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                Find your perfect home in Japan
              </motion.p> */}
            </div>
            
            {/* Stats integrated into header */}
            <StatsCards />
          </div>
        </div>
      </motion.header>
      
      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-4 pb-8">
        <Dashboard />
      </main>
      
      {/* Footer */}
      {/* <motion.footer 
        className="relative z-10 py-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        <div className="container mx-auto px-4">
          <p className="text-gray-400 text-xs text-center flex items-center justify-center gap-1">
            Made with <Heart className="w-3 h-3 text-violet-400" fill="currentColor" /> for apartment hunters
          </p>
        </div>
      </motion.footer> */}
    </div>
  )
}

export default App
