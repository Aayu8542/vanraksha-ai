import React from 'react';
import Header from '../components/Header.jsx';

export default function Landing({ onLaunch }) {
  return (
    <div className="landing-container">
      <Header />
      <main className="landing-main">
        
        <section className="hero-section hero-framed">
          <div className="tick-mark top-left"></div>
          <div className="tick-mark top-right"></div>
          <div className="tick-mark bottom-left"></div>
          <div className="tick-mark bottom-right"></div>

          <div className="hero-content">
            <h1 className="hero-title">From 3-hour satellite delays to real-time wildfire intelligence.</h1>
            <p className="hero-subtitle">VanaRaksha provides satellite-triggered detection, ground-ranger verification, and physics-based fire spread simulation to support rapid fire detection and response.</p>
            <div className="hero-cta">
              <button className="btn-primary" onClick={onLaunch}>Open the field desk</button>
              <a className="btn-outline" href="#how-it-works">See how it works</a>
            </div>
          </div>
          
          <div className="hero-login-preview">
            <div className="login-card-inner">
              <h3 className="login-preview-heading">Ranger Access</h3>
              <p className="login-preview-copy">Field teams confirm alerts and verify fires here</p>
              
              <div className="fake-input-group">
                <div className="fake-input">Email address</div>
                <div className="fake-input">Password</div>
              </div>
              
              <a href="/login.html" className="btn-primary login-preview-btn">Go to Ranger Login</a>
            </div>
            <div className="map-caption">RANGER ACCESS</div>
          </div>
        </section>

        <section className="full-width-map-section">
          <div className="large-map-preview">
            <div className="static-map-container">
              <div className="static-pin pin-high"></div>
              <div className="static-pin pin-extreme pulse-animation"></div>
              <div className="static-pin pin-moderate"></div>
              <div className="static-pin pin-very-high"></div>
            </div>
            <div className="map-caption">Live detection preview</div>
          </div>
        </section>

        <section className="stats-section">
          <div className="stat-block">
            <div className="stat-number">21.76%</div>
            <div className="stat-label">of India's geographical area is forest cover</div>
          </div>
          <div className="stat-block">
            <div className="stat-number">715,343 sq km</div>
            <div className="stat-label">total forest cover (ISFR 2023)</div>
          </div>
          <div className="stat-block">
            <div className="stat-number">+156 sq km</div>
            <div className="stat-label">net forest cover increase since ISFR 2021</div>
          </div>
        </section>

        <footer className="citation-strip">
          VANARAKSHA AI &middot; CONSERVATION OPERATIONS DESK &middot; DATA SOURCES: NASA FIRMS &middot; ISRO BHUVAN &middot; FSI ISFR 2023
        </footer>
      </main>

      <style dangerouslySetInnerHTML={{__html: `
        /* Overrides to prevent old styling leakage */
        body {
          background-color: var(--bg-paper);
          margin: 0;
        }

        .landing-container {
          min-height: calc(100vh - 72px); /* subtracting header roughly */
          display: flex;
          flex-direction: column;
          background-color: var(--bg-paper);
          position: relative;
          overflow-x: hidden;
        }

        .landing-main::before {
          content: '';
          position: fixed;
          top: -50%; left: -50%; right: -50%; bottom: -50%;
          background-image: url("data:image/svg+xml,%3Csvg width='400' height='400' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M10 50 Q 150 10 200 100 T 380 150 M 50 150 Q 150 200 250 150 T 390 50 M 100 200 Q 200 150 300 200 T 400 200 M 50 250 Q 150 300 250 250 T 350 250 M 100 300 Q 200 350 300 300 T 400 300 M 150 350 Q 250 300 350 350 T 450 350 M 200 400 Q 300 350 350 400 T 450 450' fill='none' stroke='%23D8D6CB' stroke-width='1' stroke-opacity='0.4'/%3E%3C/svg%3E");
          background-size: 400px 400px;
          z-index: 0;
          pointer-events: none;
          animation: bgDrift 60s linear infinite;
        }

        @media (prefers-reduced-motion: reduce) {
          .landing-main::before {
            animation: none;
          }
        }

        @keyframes bgDrift {
          from { transform: translate(0, 0); }
          to { transform: translate(100px, 100px); }
        }

        .landing-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          position: relative;
          z-index: 1;
          padding: 0 2rem;
        }

        .hero-framed {
          position: relative;
          display: flex;
          flex-direction: row;
          align-items: center;
          justify-content: space-between;
          padding: 4rem 0;
          margin: 0 auto;
          max-width: 1100px;
          width: 100%;
          gap: 4rem;
          box-sizing: border-box;
        }

        @media (max-width: 768px) {
          .hero-framed {
            flex-direction: column;
            padding: 4rem 0;
          }
        }

        .tick-mark {
          position: absolute;
          width: 24px;
          height: 24px;
          border-color: var(--border-hairline);
          border-style: solid;
          border-width: 0;
        }
        .top-left { top: 0; left: 0; border-top-width: 1px; border-left-width: 1px; }
        .top-right { top: 0; right: 0; border-top-width: 1px; border-right-width: 1px; }
        .bottom-left { bottom: 0; left: 0; border-bottom-width: 1px; border-left-width: 1px; }
        .bottom-right { bottom: 0; right: 0; border-bottom-width: 1px; border-right-width: 1px; }

        .hero-content {
          flex: 1;
          max-width: 550px;
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .hero-title {
          font-family: var(--font-display);
          color: var(--ink-primary);
          font-weight: 500;
          font-size: 3rem;
          line-height: 1.1;
          margin-bottom: 1.5rem;
          margin-top: 0;
        }

        .hero-subtitle {
          font-family: var(--font-body);
          color: var(--ink-muted);
          font-size: 1.125rem;
          line-height: 1.6;
          margin-bottom: 2rem;
        }

        .hero-cta {
          display: flex;
          gap: 1rem;
        }

        .btn-primary {
          background-color: var(--ink-primary);
          color: var(--bg-paper);
          font-family: var(--font-body);
          padding: 0.75rem 1.5rem;
          border: none;
          cursor: pointer;
          font-size: 0.875rem;
          font-weight: 500;
          border-radius: 4px;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          transition: opacity 0.2s;
        }
        
        .btn-primary:hover {
          opacity: 0.9;
        }

        .btn-outline {
          background-color: transparent;
          color: var(--ink-primary);
          border: 1px solid var(--ink-primary);
          padding: 0.75rem 1.5rem;
          cursor: pointer;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          font-family: var(--font-body);
          font-size: 0.875rem;
          font-weight: 500;
          border-radius: 4px;
        }

        .hero-login-preview {
          flex: 0 0 40%;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          width: 100%;
        }

        .login-card-inner {
          width: 100%;
          background-color: var(--bg-paper);
          border: 1px solid var(--border-hairline);
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 2.5rem;
          box-sizing: border-box;
          border-radius: 4px;
        }

        .login-preview-heading {
          font-family: var(--font-display);
          font-size: 1.5rem;
          color: var(--ink-primary);
          margin: 0 0 0.5rem 0;
          font-weight: 500;
        }

        .login-preview-copy {
          font-family: var(--font-body);
          font-size: 0.875rem;
          color: var(--ink-muted);
          margin: 0 0 1.5rem 0;
        }

        .fake-input-group {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }

        .fake-input {
          border: 1px solid var(--border-hairline);
          background-color: var(--bg-paper);
          padding: 0.75rem 1rem;
          font-family: var(--font-body);
          font-size: 0.875rem;
          color: var(--ink-muted);
          opacity: 0.7;
          border-radius: 4px;
          cursor: not-allowed;
          box-sizing: border-box;
        }

        .login-preview-btn {
          text-align: center;
          display: block;
          width: 100%;
          box-sizing: border-box;
        }

        .full-width-map-section {
          width: 100%;
          max-width: 1100px;
          margin: 0 auto;
          padding: 4rem 0;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          border-top: 1px solid var(--border-hairline);
        }

        .large-map-preview {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .static-map-container {
          width: 100%;
          aspect-ratio: 21/9;
          background-color: var(--bg-map-dark);
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 400' preserveAspectRatio='xMidYMid slice'%3E%3Cg fill='none' stroke='%23EDEEE6' stroke-width='0.5' stroke-opacity='0.08'%3E%3Cpath d='M 0 100 Q 200 50, 400 150 T 1000 100' /%3E%3Cpath d='M 0 200 Q 250 120, 500 250 T 1000 200' /%3E%3Cpath d='M 0 300 Q 300 250, 600 350 T 1000 300' /%3E%3Cpath d='M 150 0 Q 200 150, 100 400' /%3E%3Cpath d='M 350 0 Q 300 200, 400 400' /%3E%3Cpath d='M 600 0 Q 550 250, 700 400' /%3E%3Cpath d='M 800 0 Q 900 150, 850 400' /%3E%3C/g%3E%3Cg fill='none' stroke='%23EDEEE6' stroke-width='1.5' stroke-opacity='0.1'%3E%3Cpath d='M -100 150 Q 300 400, 700 100 T 1200 250' /%3E%3Cpath d='M 400 -50 Q 500 200, 200 500' /%3E%3C/g%3E%3C/svg%3E");
          background-size: cover;
          background-position: center;
          border-radius: 4px;
          border: 1px solid var(--border-hairline);
          position: relative;
          overflow: hidden;
        }

        .static-pin {
          position: absolute;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          border: 2px solid var(--ink-primary);
          transform: translate(-50%, -50%);
        }

        .pin-high { top: 35%; left: 45%; background-color: var(--risk-high); }
        .pin-extreme { top: 42%; left: 32%; background-color: var(--risk-extreme); }
        .pin-moderate { top: 60%; left: 55%; background-color: var(--risk-moderate); }
        .pin-very-high { top: 50%; left: 40%; background-color: var(--risk-very-high); }

        .pulse-animation {
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(107, 27, 27, 0.7); }
          70% { box-shadow: 0 0 0 10px rgba(107, 27, 27, 0); }
          100% { box-shadow: 0 0 0 0 rgba(107, 27, 27, 0); }
        }

        .map-caption {
          font-family: monospace;
          color: var(--ink-muted);
          font-size: 0.75rem;
          text-align: left;
          text-transform: uppercase;
        }

        .stats-section {
          width: 100%;
          max-width: 1100px;
          margin: 0 auto;
          padding: 4rem 0;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 2rem;
          border-top: 1px solid var(--border-hairline);
          box-sizing: border-box;
        }

        @media (max-width: 768px) {
          .stats-section {
            grid-template-columns: 1fr;
            text-align: center;
          }
        }

        .stat-block {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .stat-number {
          font-family: var(--font-display);
          font-size: 2.5rem;
          color: var(--ink-primary);
          line-height: 1;
        }

        .stat-label {
          font-family: var(--font-body);
          font-size: 0.875rem;
          color: var(--ink-muted);
        }

        .citation-strip {
          margin: 0 auto;
          font-family: monospace;
          color: var(--ink-muted);
          font-size: 0.75rem;
          padding: 2rem 0;
          text-align: center;
          width: 100%;
          max-width: 1100px;
          border-top: 1px solid var(--border-hairline);
        }
      `}} />
    </div>
  );
}
