import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText('AI Image Gen')).toBeInTheDocument();
  });

  it('renders the Generate page by default', () => {
    render(<App />);
    expect(screen.getByText('Generate Image')).toBeInTheDocument();
  });

  it('provides navigation links', () => {
    render(<App />);
    expect(screen.getAllByRole('link', { name: /generate/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /gallery/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /history/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /presets/i }).length).toBeGreaterThanOrEqual(1);
  });
});
