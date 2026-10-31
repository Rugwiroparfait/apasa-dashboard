import * as React from "react"
import { createRoot } from "react-dom/client"
import { Button } from "./components/ui/button"
import { Card } from "./components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "./components/ui/popover"
import { initAssistant } from "../evidence/static/evidence/assistant.js"

// Django supplies the authenticated, signed context and conversation markup.
// Reparenting preserves the existing form, CSRF token, listeners and chat history.
const panel = document.getElementById("apasa-assistant")!
const mount = document.getElementById("assistant-launcher")
function ChatContent({ onClose }: { onClose: () => void }) {
  const host = React.useRef<HTMLDivElement>(null)
  React.useLayoutEffect(() => {
    host.current!.append(panel)
    panel.hidden = false
    const close = panel.querySelector<HTMLButtonElement>(".assistant-close")!
    close.addEventListener("click", onClose)
    const thread = panel.querySelector(".assistant-thread")!
    thread.scrollTop = thread.scrollHeight
    return () => { close.removeEventListener("click", onClose); panel.hidden = true }
  }, [onClose])
  return <Card><div ref={host} className="h-full min-h-0" /></Card>
}
function Assistant() {
  const [open, setOpen] = React.useState(false)
  const close = React.useCallback(() => setOpen(false), [])
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button type="button" className="assistant-toggle" aria-label={open ? "Close APASA Assistant" : "Open APASA Assistant"}>
          <svg className="size-5" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><use href={`${panel.dataset.iconUrl}#message-circle`} /></svg>
          <span>APASA Assistant</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="apasa-chat-popover"
        align="start" side="top" sideOffset={12} collisionPadding={12}
        aria-labelledby="assistant-heading"
        style={{ height: "min(620px, calc(var(--radix-popover-content-available-height) - 4px))", maxHeight: "calc(100dvh - 100px)" }}
        onOpenAutoFocus={event => { event.preventDefault(); panel.querySelector<HTMLButtonElement>(".assistant-close")?.focus() }}
      >
        <ChatContent onClose={close} />
      </PopoverContent>
    </Popover>
  )
}
if (mount && panel) {
  initAssistant(panel)
  createRoot(mount).render(<Assistant />)
}

// Charts share the same shadcn/Tailwind runtime; no separate provider or data API.
import { mountCharts } from "./charts"
mountCharts()
