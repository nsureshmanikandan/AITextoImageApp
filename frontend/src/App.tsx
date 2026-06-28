import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { GeneratePage } from './features/prompt/GeneratePage';
import { ImageGallery } from './features/gallery/ImageGallery';
import { PromptHistory } from './features/history/PromptHistory';
import { PresetManager } from './features/presets/PresetManager';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
    mutations: {
      retry: 0,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<GeneratePage />} />
              <Route path="/gallery" element={<ImageGallery />} />
              <Route path="/history" element={<PromptHistory />} />
              <Route path="/presets" element={<PresetManager />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
