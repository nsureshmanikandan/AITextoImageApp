import { motion } from 'framer-motion'
import { Video, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface EmptyStateProps {
  title?: string
  description?: string
  showCTA?: boolean
}

export default function EmptyState({
  title = 'No videos yet',
  description = 'Create your first AI video by pasting a news article URL.',
  showCTA = true,
}: EmptyStateProps) {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-24 text-center"
    >
      <div className="w-20 h-20 rounded-2xl bg-navy-800/80 border border-white/10 flex items-center justify-center mb-6">
        <Video className="w-10 h-10 text-navy-600" />
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-slate-400 max-w-sm mb-8">{description}</p>
      {showCTA && (
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => navigate('/create')}
        >
          <Plus className="w-4 h-4" />
          Create New Video
        </button>
      )}
    </motion.div>
  )
}
