import { AnimatePresence } from 'framer-motion'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import BreakingAlert from './components/BreakingAlert'
import Layout from './components/Layout'
import ApprovalQueue from './pages/ApprovalQueue'
import CreateVideo from './pages/CreateVideo'
import Dashboard from './pages/Dashboard'
import FeedConfigPage from './pages/FeedConfigPage'
import History from './pages/History'
import LiveNewsDashboard from './pages/LiveNewsDashboard'
import NotFound from './pages/NotFound'
import Review from './pages/Review'

export default function App() {
  return (
    <BrowserRouter>
      <BreakingAlert />
      <AnimatePresence mode="wait">
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="create" element={<CreateVideo />} />
            <Route path="review/:id" element={<Review />} />
            <Route path="history" element={<History />} />
            <Route path="live-news" element={<LiveNewsDashboard />} />
            <Route path="live-news/queue" element={<ApprovalQueue />} />
            <Route path="live-news/feeds" element={<FeedConfigPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AnimatePresence>
    </BrowserRouter>
  )
}
