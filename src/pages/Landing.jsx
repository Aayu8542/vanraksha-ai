import React, { useState, useEffect } from 'react';
import { ALERTS, PROTECTED_ZONES, SPECIES_DATA } from '../data/data';

export default function Landing({ onLaunch }) {
  const [stats, setStats] = useState({
    activeAlerts: ALERTS.filter(a => a.type === 'critical').length,
    protectedZones: PROTECTED_ZONES.length,
    endangeredSpecies: SPECIES_DATA.filter(s => s.status === 'CR' || s.status === 'EN').length,
    treesMonitored: 2400000
  });

  // Simulate real-time monitoring feel
  useEffect(() => {
    const t = setInterval(() => {
      setStats(prev => ({
        ...prev,
        treesMonitored: prev.treesMonitored + Math.floor(Math.random() * 5)
      }));
    }, 2500);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="landing-container">
      <nav className="landing-nav">
        <div className="landing-logo">
          <span className="logo-icon">VR</span>
          <span className="logo-text">VanaRaksha<span className="highlight"> / field intelligence</span></span>
        </div>
        <span className="landing-live-status"><span className="landing-live-dot"></span>Live</span>
      </nav>

      <main className="landing-main">
        <section className="hero-section">
          <div className="badge-pill"><span className="pulse-dot"></span>Conservation operations desk</div>
          <p className="hero-kicker">India's forests are changing faster than field teams can respond.</p>
          <h1 className="hero-title">Turn scattered signals into <span className="text-gradient">timely action.</span></h1>
          <p className="hero-subtitle">VanaRaksha brings maps, alerts, species risk, field observations, and open-source intelligence into one practical workspace for protecting vulnerable ecosystems.</p>
          <div className="hero-cta">
            <button className="btn-primary btn-glow btn-large" onClick={onLaunch}>Open the field desk <span aria-hidden="true">→</span></button>
            <a className="btn-outline btn-large" href="#approach">See how it works</a>
          </div>
        </section>

        <section className="landing-brief" id="approach">
          <div className="brief-intro">
            <p className="section-kicker">The problem</p>
            <h2>Conservation decisions are made with incomplete context.</h2>
            <p>Signals arrive from satellites, sensors, reports, and communities, but they rarely arrive together. That delay makes it harder to spot threats early, prioritize patrols, and protect wildlife corridors before damage compounds.</p>
          </div>
          <div className="brief-list">
            <article className="brief-item"><span>01</span><div><h3>See change early</h3><p>Surface fire, deforestation, air quality, and habitat signals before they become a crisis.</p></div></article>
            <article className="brief-item"><span>02</span><div><h3>Understand the place</h3><p>Connect protected zones, species pressure, terrain, and live observations in one view.</p></div></article>
            <article className="brief-item"><span>03</span><div><h3>Act with confidence</h3><p>Give teams a shared evidence base for patrol planning, reporting, and rapid response.</p></div></article>
          </div>
        </section>

        <section className="impact-section">
          <div className="impact-heading"><p className="section-kicker">The intended impact</p><h2>More time protecting forests. Less time assembling the picture.</h2></div>
          <div className="impact-grid">
            <div><strong>Earlier</strong><span>threat detection</span></div>
            <div><strong>Clearer</strong><span>field priorities</span></div>
            <div><strong>Stronger</strong><span>protection decisions</span></div>
          </div>
        </section>

        <section className="stats-ticker" aria-label="Current monitoring coverage">
          <div className="stat-item"><span className="stat-value text-red">{stats.activeAlerts}</span><span className="stat-label">Critical alerts</span></div>
          <div className="stat-divider"></div>
          <div className="stat-item"><span className="stat-value text-green">{stats.protectedZones}</span><span className="stat-label">Protected zones</span></div>
          <div className="stat-divider"></div>
          <div className="stat-item"><span className="stat-value text-yellow">{stats.endangeredSpecies}</span><span className="stat-label">Species at risk</span></div>
          <div className="stat-divider"></div>
          <div className="stat-item"><span className="stat-value text-blue">{(stats.treesMonitored / 1000000).toFixed(2)}M+</span><span className="stat-label">Hectares monitored</span></div>
        </section>
      </main>
    </div>
  );
}
