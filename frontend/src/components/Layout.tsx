import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: ReactNode;
}

function IconSparkles({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v1m0 16v1M4.22 4.22l.7.7m12.16 12.16.7.7M3 12h1m16 0h1M4.22 19.78l.7-.7M18.36 5.64l.7-.7" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}

function IconImages({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="9" cy="9" r="2" />
      <path d="M21 15l-5-5L5 21" />
    </svg>
  );
}

function IconHistory({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l4 2" />
    </svg>
  );
}

function IconSliders({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="9" cy="6" r="2" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
      <circle cx="9" cy="18" r="2" fill="currentColor" stroke="none" />
    </svg>
  );
}

const navItems = [
  { path: '/',         label: 'Generate', Icon: IconSparkles },
  { path: '/gallery',  label: 'Gallery',  Icon: IconImages   },
  { path: '/history',  label: 'History',  Icon: IconHistory  },
  { path: '/presets',  label: 'Presets',  Icon: IconSliders  },
];

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="flex min-h-dvh bg-ink">
      {/* Sidebar — desktop */}
      <nav
        className="hidden md:flex flex-col w-60 shrink-0 border-r border-white/5 bg-surface p-5"
        aria-label="Main navigation"
      >
        {/* Brand */}
        <div className="mb-10 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center glow-violet shrink-0">
            <IconSparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-base font-semibold gradient-brand text-glow">
            AI Image Gen
          </span>
        </div>

        <ul className="space-y-1" role="list">
          {navItems.map(({ path, label, Icon }) => {
            const active = location.pathname === path;
            return (
              <li key={path}>
                <Link
                  to={path}
                  aria-current={active ? 'page' : undefined}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 cursor-pointer ${
                    active
                      ? 'bg-brand-600/20 text-brand-400 glow-violet'
                      : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-5 h-5 shrink-0 ${active ? 'text-brand-400' : 'text-slate-500'}`} />
                  {label}
                  {active && (
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-500" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Footer hint */}
        <div className="mt-auto pt-6 border-t border-white/5">
          <p className="text-xs text-slate-600 leading-relaxed">
            Powered by Flux 2.0 Pro &amp; GPT-4o
          </p>
        </div>
      </nav>

      {/* Bottom nav — mobile */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-50 border-t border-white/5 bg-surface/95 backdrop-blur-md"
        aria-label="Mobile navigation"
      >
        <ul className="flex justify-around py-2 px-1" role="list">
          {navItems.map(({ path, label, Icon }) => {
            const active = location.pathname === path;
            return (
              <li key={path}>
                <Link
                  to={path}
                  aria-current={active ? 'page' : undefined}
                  className={`flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors duration-150 min-h-[44px] min-w-[44px] justify-center ${
                    active ? 'text-brand-400' : 'text-slate-500'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${active ? 'text-brand-400' : 'text-slate-500'}`} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Main content */}
      <main className="flex-1 min-w-0 p-4 md:p-8 pb-24 md:pb-8 overflow-auto">
        {children}
      </main>
    </div>
  );
}
