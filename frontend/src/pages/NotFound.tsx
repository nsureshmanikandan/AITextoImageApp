import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Home, AlertTriangle } from 'lucide-react'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="page-container flex items-center justify-center min-h-[70vh]">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center"
      >
        <div className="w-20 h-20 rounded-2xl bg-gold-400/10 border border-gold-400/20 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-10 h-10 text-gold-400" />
        </div>

        <h1 className="text-6xl font-black text-white mb-3">
          <span className="text-gradient-azure">404</span>
        </h1>
        <h2 className="text-xl font-semibold text-white mb-2">Page not found</h2>
        <p className="text-slate-400 text-sm mb-8 max-w-sm mx-auto">
          The page you're looking for doesn't exist or has been moved.
        </p>

        <button
          onClick={() => navigate('/')}
          className="btn-primary flex items-center gap-2 mx-auto"
        >
          <Home className="w-4 h-4" />
          Back to Dashboard
        </button>
      </motion.div>
    </div>
  )
}
