import React from 'react';
import ChartCard from '../components/ChartCard.jsx';
import { YEARLY_DATA, STATE_LOSS } from '../data/data.js';
export default function Timeline(){
 const common={borderColor:'#3dcc73',backgroundColor:'rgba(61,204,115,.08)',fill:true,tension:.4,pointRadius:2};
 return <section className="full-view"><div className="view-header"><h1>📊 Historical Forest Cover Timeline</h1><p>India's forest cover change from 2000 to 2024 based on the project's seeded time-series data</p></div><div className="timeline-grid">
  <ChartCard title="Forest Cover (km²) — 2000 to 2024" labels={YEARLY_DATA.years} dataset={{...common,data:YEARLY_DATA.forestCover}}/>
  <ChartCard type="bar" title="Annual Forest Loss by State (Top 8)" labels={STATE_LOSS.states} dataset={{data:STATE_LOSS.loss2024,backgroundColor:'rgba(245,158,11,.7)',borderRadius:4}}/>
  <ChartCard title="NDVI Mean Score — India" labels={YEARLY_DATA.years} dataset={{...common,data:YEARLY_DATA.ndvi,borderColor:'#5de896'}}/>
  <ChartCard title="Carbon Stock Decline (Tg C)" labels={YEARLY_DATA.years} dataset={{...common,data:YEARLY_DATA.carbonStock,borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,.08)'}}/>
 </div></section>;
}
