import { create } from 'zustand'
import type { Job } from '../types'

interface JobStore {
  jobs: Job[]
  currentJob: Job | null
  isLoading: boolean
  error: string | null

  setJobs: (jobs: Job[]) => void
  setCurrentJob: (job: Job | null) => void
  updateJob: (job: Job) => void
  addJob: (job: Job) => void
  removeJob: (id: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useJobStore = create<JobStore>((set) => ({
  jobs: [],
  currentJob: null,
  isLoading: false,
  error: null,

  setJobs: (jobs) => set({ jobs }),

  setCurrentJob: (job) => set({ currentJob: job }),

  updateJob: (job) =>
    set((state) => ({
      jobs: state.jobs.map((j) => (j.id === job.id ? job : j)),
      currentJob: state.currentJob?.id === job.id ? job : state.currentJob,
    })),

  addJob: (job) =>
    set((state) => ({
      jobs: [job, ...state.jobs],
      currentJob: job,
    })),

  removeJob: (id) =>
    set((state) => ({
      jobs: state.jobs.filter((j) => j.id !== id),
      currentJob: state.currentJob?.id === id ? null : state.currentJob,
    })),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}))
