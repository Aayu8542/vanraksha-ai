import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
export default function ChartCard({ title, type='line', labels, dataset, options={}, height=220 }) {
  const ref=useRef(null), instance=useRef(null);
  useEffect(()=>{if(!ref.current)return;instance.current?.destroy();instance.current=new Chart(ref.current,{type,data:{labels,datasets:[dataset]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(61,204,115,.07)'},ticks:{color:'rgba(200,240,218,.45)'}},y:{grid:{color:'rgba(61,204,115,.07)'},ticks:{color:'rgba(200,240,218,.45)'}}},...options}});return()=>instance.current?.destroy()},[labels,dataset,type,options]);
  return <div className="tl-chart-card" style={{height}}><h3>{title}</h3><div style={{position:'relative',height:'calc(100% - 36px)'}}><canvas ref={ref}/></div></div>;
}
