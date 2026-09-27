import React from 'react';

export default function Header({ activeView, onNavigate }) {
  return (
    <header className="global-header">
      <div className="header-left">
        <div className="logo-lockup" onClick={() => onNavigate && onNavigate('landing')} style={{cursor: 'pointer'}}>
          <div className="logo-swatch"></div>
          <div className="logo-text">
            <span className="logo-name">VanaRaksha</span>
            <span className="logo-tag">AI FOREST INTELLIGENCE</span>
          </div>
        </div>
      </div>
      
      <nav className="header-nav">
        <a href="#home" onClick={(e) => { e.preventDefault(); onNavigate && onNavigate('landing'); }} className="nav-link">Home</a>
        <a href="#how-it-works" className="nav-link">How It Works</a>
        <a href="#methodology" className="nav-link">Methodology</a>
      </nav>
      <style>{`
        .global-header {
          background-color: var(--bg-paper);
          border-bottom: 1px solid var(--border-hairline);
          box-shadow: none;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem 2rem;
        }
        .logo-lockup { display: flex; align-items: center; gap: 0.75rem; }
        .logo-swatch { width: 24px; height: 24px; background-color: var(--accent-forest); }
        .logo-text { display: flex; flex-direction: column; }
        .logo-name { font-family: var(--font-display); font-weight: bold; font-size: 1.25rem; line-height: 1; color: var(--ink-primary); }
        .logo-tag { font-family: var(--font-body); font-size: 0.65rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--ink-muted); margin-top: 0.125rem; }
        .header-nav { display: flex; gap: 1.5rem; }
        .header-nav .nav-link { font-family: var(--font-body); color: var(--ink-primary); text-decoration: none; font-size: 0.875rem; }
        .header-nav .nav-link:hover { text-decoration: underline; }
      `}</style>
    </header>
  );
}
