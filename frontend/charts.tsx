import * as React from "react"
import { createRoot } from "react-dom/client"
import { Button } from "./components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./components/ui/dialog"

type Bar = { label: string; display: string; value: string | number | null; available: boolean; percent: number; zero?: boolean; highlight?: boolean; mocked?: boolean; season_class?: string; state: string; source: string }
type Chart = { title: string; unit: string; description: string; scale_label: string; has_mock?: boolean; bars: Bar[] }
function capacity() {
  const mobile = window.innerWidth < 640
  return Math.max(2, Math.min(mobile ? 8 : 15, Math.floor((window.innerHeight - 250) / (mobile ? 48 : 32))))
}
function ChartDialog({ chart, label = "View chart" }: { chart: Chart; label?: string }) {
  const [open, setOpen] = React.useState(false)
  const [view, setView] = React.useState<'chart' | 'sources'>('chart')
  const [page, setPage] = React.useState(0)
  const [pageSize, setPageSize] = React.useState(capacity)
  React.useEffect(() => {
    const resize = () => { setPageSize(capacity()); setPage(0) }
    window.addEventListener('resize', resize, {passive: true})
    return () => window.removeEventListener('resize', resize)
  }, [])
  const total = chart.bars.length
  const start = page * pageSize
  const bars = chart.bars.slice(start, start + pageSize)
  const pages = Math.ceil(total / pageSize)
  return <Dialog open={open} onOpenChange={value => { setOpen(value); if (value) { setView('chart'); const selected = chart.bars.findIndex(bar => bar.highlight); setPage(selected < 0 ? 0 : Math.floor(selected / pageSize)) } }}>
    <DialogTrigger asChild><Button type="button" variant="outline" className="chart-open-button min-h-11 gap-2"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>{label}</Button></DialogTrigger>
    <DialogContent className="apasa-chart-dialog" style={{width: 'min(1280px, calc(100vw - 24px))', maxWidth: 'none', height: 'min(860px, calc(100dvh - 24px))'}}>
      <DialogHeader className="chart-dialog-heading">
        <DialogTitle>{chart.title}</DialogTitle>
        <DialogDescription>{chart.description}</DialogDescription>
      </DialogHeader>
      <div className="chart-dialog-toolbar">
        <div role="group" aria-label="Chart display" className="chart-view-switch">
          <Button type="button" variant={view === 'chart' ? 'default' : 'ghost'} aria-pressed={view === 'chart'} onClick={() => setView('chart')}>Chart</Button>
          <Button type="button" variant={view === 'sources' ? 'default' : 'ghost'} aria-pressed={view === 'sources'} onClick={() => setView('sources')}>Exact values &amp; sources</Button>
        </div>
        <span className="chart-unit">Unit: <strong>{chart.unit}</strong></span>
      </div>
      {chart.has_mock && <p className="chart-mock-notice">Demo series · Synthetic / illustrative — not official statistics.</p>}
      {view === 'chart' ? <div className="chart-dialog-plot" role="group" aria-label={`${chart.title}. Shared zero-based scale, ${chart.unit}.`}>
        <div className="chart-fit-rows" style={{gridTemplateRows: `repeat(${Math.max(1, bars.length)}, minmax(0, 1fr))`}}>
          {bars.map((bar, index) => <div key={`${start + index}-${bar.label}`} className={`chart-fit-row ${bar.highlight ? 'is-selected' : ''} ${bar.mocked ? 'is-mock' : ''}`} title={`${bar.label}: ${bar.available ? bar.value : 'Unavailable'} ${chart.unit} · ${bar.state} · ${bar.source}`}>
            <span className="chart-fit-label">{bar.label}{bar.highlight && <span className="chart-selected-label">Selected</span>}</span>
            <span className="chart-fit-track" aria-hidden="true">{bar.available && <span className={`${bar.season_class || ''} ${bar.zero ? 'is-zero' : ''}`} style={{width: `${bar.percent}%`}} />}</span>
            <span className="chart-fit-value">{bar.display}{bar.mocked && <small aria-label="Synthetic / illustrative — not official statistics.">Synthetic</small>}</span>
          </div>)}
        </div>
        <div className="chart-fit-axis" aria-label={`Scale: 0 to ${chart.scale_label} ${chart.unit}`}><span aria-hidden="true"/><span className="chart-axis-range"><span>0</span><span>{chart.scale_label}</span></span><span aria-hidden="true"/></div>
      </div> : <div className="chart-dialog-sources" tabIndex={0} role="region" aria-label="Exact chart values and source references"><table><caption>Original values, units, evidence states and source references</caption><thead><tr><th>Category / period</th><th>Exact value ({chart.unit})</th><th>State</th><th>Source</th></tr></thead><tbody>{chart.bars.map((bar, index) => <tr key={index}><th>{bar.label}</th><td>{bar.available ? bar.value : 'Unavailable'}</td><td>{bar.state}</td><td>{bar.source}</td></tr>)}</tbody></table></div>}
      <div className="chart-dialog-footer">
        <p>Zero baseline · Source units unchanged · Missing is not zero.</p>
        {view === 'chart' && pages > 1 && <div className="chart-pagination" aria-label="Chart pages"><Button type="button" variant="outline" aria-label="Previous chart page" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button><span role="status">{start + 1}–{Math.min(start + pageSize, total)} of {total}</span><Button type="button" variant="outline" aria-label="Next chart page" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</Button></div>}
      </div>
    </DialogContent>
  </Dialog>
}
export function mountCharts() {
  const mounts: {host: HTMLElement; id: string}[] = []
  document.querySelectorAll<HTMLElement>('[data-chart-popup]').forEach(figure => {
    const host = document.createElement('div'); host.className = 'chart-dialog-mount'
    figure.querySelector('figcaption')!.after(host)
    mounts.push({host, id: figure.dataset.chartPopup!})
  })
  document.querySelectorAll<HTMLElement>('.chart-dialog-mount[data-chart-json]').forEach(host => mounts.push({host, id: host.dataset.chartJson!}))
  mounts.forEach(({host, id}) => {
    const source = document.getElementById(id)
    if (!source) return
    try {
      const chart = JSON.parse(source.textContent || '') as Chart
      if (!Array.isArray(chart.bars)) return
      createRoot(host).render(<ChartDialog chart={chart} label={host.dataset.chartLabel} />)
      host.closest('[data-chart-popup]')?.classList.add('chart-enhanced')
      if (host.matches('[data-chart-json]')) document.querySelectorAll<HTMLElement>('[data-chart-fallback]').forEach(element => element.hidden = true)
    } catch { /* The native chart and exact-value table remain the fallback. */ }
  })
}
