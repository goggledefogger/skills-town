// Records a web app's flow as screen clips and wraps them in a captioned HyperFrames video.
//   node walkthrough.ts <walkthrough.json> [--scenes 1,3] [--render]
//   node walkthrough.ts --selftest
//   node walkthrough.ts --check      (are Chrome, ffmpeg and npx here?)
// The JSON is the whole script: how to start the app, the scenes, their steps and captions.
// Output lands in a `video/` folder beside the JSON: assets/ (clips), compositions/, index.html, renders/.
// Zero packages: Node 22, ffmpeg and Chrome. HyperFrames runs through npx only when --render is given.
import { spawn, spawnSync } from 'node:child_process'
import type { ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'

const HYPERFRAMES = 'hyperframes@0.8.188'
const CARD = 2 // seconds of title card before each clip
const W = 1920
const H = 1080

type Step = Record<string, any>
type Scene = { title: string; reload?: boolean; before?: Step[]; steps: Step[] }
type Config = {
  title?: string
  url: string
  start?: { command: string; cwd?: string }
  viewport?: [number, number]
  theme?: { ground?: string; ink?: string; accent?: string; font?: string }
  scenes: Scene[]
}
type Recorded = { title: string; duration: number; captions: { at: number; text: string }[] }

// ---------- the video project (pure, covered by --selftest) ----------

const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const r2 = (n: number): number => Math.round(n * 100) / 100

export function sceneHtml(i: number, total: number, s: Recorded, view: [number, number]): string {
  const id = `s${i}`
  const box = fit(view)
  const caps = s.captions.map((c, k) => {
    const start = CARD + c.at
    const end = CARD + (s.captions[k + 1]?.at ?? s.duration)
    return { id: `${id}-cap${k + 1}`, start: r2(start), dur: r2(Math.max(0.5, end - start)), text: c.text }
  })
  return `<template>
  <style>
    #root { position: absolute; inset: 0; background: var(--ground); font-family: var(--font); }
    .${id}-card { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 24px; color: var(--ink); }
    .${id}-num { font-size: 40px; color: var(--accent); font-weight: 600; }
    .${id}-title { font-size: 96px; font-weight: 700; letter-spacing: -0.02em; text-align: center; max-width: 1500px; }
    .${id}-shot { position: absolute; left: ${box.left}px; top: ${box.top}px; width: ${box.width}px; height: ${box.height}px; border-radius: 14px; box-shadow: 0 20px 60px rgba(0, 0, 0, .45); background: var(--ground); }
    .${id}-cap { position: absolute; left: 120px; right: 120px; top: ${box.top + box.height + 22}px; text-align: center; color: var(--ink); font-size: 44px; font-weight: 500; }
  </style>
  <div id="root" data-composition-id="${id}" data-width="${W}" data-height="${H}">
    <div id="${id}-card" class="clip ${id}-card" data-start="0" data-duration="${CARD + 0.2}" data-track-index="0">
      <div id="${id}-num" class="${id}-num">${i} of ${total}</div>
      <div id="${id}-title" class="${id}-title">${esc(s.title)}</div>
    </div>
    <video id="${id}-video" class="clip ${id}-shot" src="assets/scene-${i}.mp4" data-start="${CARD}" data-duration="${r2(s.duration)}" data-track-index="1" muted playsinline></video>
${caps.map((c) => `    <div id="${c.id}" class="clip ${id}-cap" data-start="${c.start}" data-duration="${c.dur}" data-track-index="2">${esc(c.text)}</div>`).join('\n')}
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.fromTo("#${id}-num", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, 0.1);
    tl.fromTo("#${id}-title", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 0.25);
    tl.fromTo("#${id}-video", { opacity: 0 }, { opacity: 1, duration: 0.4 }, ${CARD});
${caps.map((c) => `    tl.fromTo("#${c.id}", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.3 }, ${c.start});`).join('\n')}
    window.__timelines["${id}"] = tl;
  </script>
</template>
`
}

export function indexHtml(scenes: Recorded[], theme: Config['theme'] = {}): string {
  let at = 0
  const hosts = scenes.map((s, k) => {
    const id = `s${k + 1}`
    const len = r2(CARD + s.duration)
    const host = `      <div id="${id}" data-composition-id="${id}" data-composition-src="compositions/${id}.html" data-start="${r2(at)}" data-duration="${len}" data-track-index="0" data-track-kind="graphics" data-width="${W}" data-height="${H}"></div>`
    at += len
    return host
  })
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${W}, height=${H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      :root { --ground: ${theme.ground ?? '#1d2330'}; --ink: ${theme.ink ?? '#f4f1ea'}; --accent: ${theme.accent ?? '#e8583c'}; --font: ${theme.font ?? 'Inter, sans-serif'}; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: ${W}px; height: ${H}px; overflow: hidden; background: var(--ground); }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${r2(at)}" data-width="${W}" data-height="${H}">
${hosts.join('\n')}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({ paused: true });
    </script>
  </body>
</html>
`
}

// The clip sits in the top of the frame at the app's own aspect, leaving a band for the caption
function fit([vw, vh]: [number, number]): { left: number; top: number; width: number; height: number } {
  const maxW = 1600
  const maxH = 900
  const k = Math.min(maxW / vw, maxH / vh)
  const width = Math.round(vw * k)
  const height = Math.round(vh * k)
  return { left: Math.round((W - width) / 2), top: 40, width, height }
}

function selftest(): void {
  const s: Recorded = { title: 'A <b> title', duration: 8, captions: [{ at: 0.5, text: 'one' }, { at: 4, text: 'two & more' }] }
  const html = sceneHtml(2, 3, s, [1440, 900])
  if (!html.includes('data-start="2.5" data-duration="3.5"')) throw new Error('first caption should run from its mark to the next one')
  if (!html.includes('data-start="6" data-duration="4"')) throw new Error('last caption should run to the end of the clip')
  if (!html.includes('A &lt;b&gt; title') || !html.includes('two &amp; more')) throw new Error('text must be escaped')
  if (!html.includes('window.__timelines["s2"]')) throw new Error('timeline must register under the scene id')
  const idx = indexHtml([s, { ...s, duration: 3 }])
  if (!idx.includes('id="s2" data-composition-id="s2" data-composition-src="compositions/s2.html" data-start="10" data-duration="5"')) throw new Error('scenes must follow one another')
  if (!idx.includes('data-duration="15"')) throw new Error('video length must be the sum of the scenes')
  const box = fit([390, 844])
  if (box.height !== 900 || box.left + box.width > W) throw new Error('a phone-shaped clip must fit the frame')
  console.log('selftest: ok')
}

// ---------- recording ----------

async function freePort(): Promise<number> {
  const s = createServer()
  await new Promise<void>((ok) => s.listen(0, '127.0.0.1', ok))
  const port = (s.address() as { port: number }).port
  await new Promise((ok) => s.close(ok))
  return port
}

function findChrome(): string {
  const found = [process.env.CHROME, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium', 'google-chrome', 'chromium', 'chromium-browser']
    .filter((c): c is string => !!c)
    .find((c) => (c.includes('/') && !existsSync(c) ? false : spawnSync(c, ['--version'], { timeout: 10000 }).status === 0))
  if (!found) throw new Error('No Chrome found. Install Google Chrome or set CHROME to its path.')
  return found
}

// What a run needs, checked before anything records so a missing tool is named up front
function missingTools(render: boolean): string[] {
  const has = (cmd: string, arg = '-version'): boolean => spawnSync(cmd, [arg], { timeout: 10000 }).status === 0
  const missing: string[] = []
  try { findChrome() } catch { missing.push('Chrome: install Google Chrome, or set CHROME to its path') }
  if (!has('ffmpeg')) missing.push('ffmpeg: brew install ffmpeg, or apt install ffmpeg')
  if (render && !has('npx', '--version')) missing.push('npx: comes with Node, from nodejs.org')
  return missing
}

function check(): void {
  const missing = missingTools(true)
  const print = spawnSync('pdftoppm', ['-v'], { timeout: 10000 }).status === 0
  console.log(missing.length ? `missing:\n  ${missing.join('\n  ')}` : 'ready: Chrome, ffmpeg and npx found')
  if (!print) console.log('optional: pdftoppm (poppler) for printPages steps: brew install poppler, or apt install poppler-utils')
  if (missing.length) process.exitCode = 1
}

const CURSOR = `(() => {
  if (document.getElementById('wt-cursor')) return
  const s = document.createElement('style')
  s.textContent = '#wt-cursor{position:fixed;z-index:2147483647;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;background:rgba(232,88,60,.35);border:3px solid #e8583c;pointer-events:none;transition:left .6s ease,top .6s ease,transform .15s}#wt-cursor.down{transform:scale(.7)}@media print{#wt-cursor{display:none}}'
  document.head.append(s)
  const c = document.createElement('div'); c.id = 'wt-cursor'; c.style.left = '60%'; c.style.top = '40%'
  document.body.append(c)
})()`

async function main(): Promise<void> {
  const args = process.argv.slice(2)
  if (args.includes('--selftest')) return selftest()
  if (args.includes('--check')) return check()
  const configPath = args.find((a) => !a.startsWith('--') && a.endsWith('.json'))
  if (!configPath) throw new Error('usage: node walkthrough.ts <walkthrough.json> [--scenes 1,3] [--render]')
  const missing = missingTools(args.includes('--render'))
  if (missing.length) throw new Error(`missing before recording:\n  ${missing.join('\n  ')}`)
  const here = dirname(resolve(configPath))
  const config = JSON.parse(readFileSync(configPath, 'utf8')) as Config
  const view = config.viewport ?? [1440, 900]
  const only = args.includes('--scenes') ? args[args.indexOf('--scenes') + 1].split(',').map(Number) : undefined
  const out = join(here, 'video')
  mkdirSync(join(out, 'assets'), { recursive: true })
  mkdirSync(join(out, 'compositions'), { recursive: true })

  let app: ChildProcess | undefined
  const port = await freePort()
  const base = config.url.replace('{port}', String(port))
  if (config.start) {
    app = spawn(config.start.command.replace('{port}', String(port)), { cwd: resolve(here, config.start.cwd ?? '.'), shell: true, stdio: 'ignore', detached: true })
    const stop = Date.now() + 30000
    while (Date.now() < stop) {
      try { if ((await fetch(base)).ok) break } catch { /* not up yet */ }
      await new Promise((ok) => setTimeout(ok, 200))
    }
  }

  const profile = mkdtempSync(join(tmpdir(), 'walkthrough-chrome-'))
  const chrome = spawn(findChrome(), ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] })
  try {
    const devtools = await new Promise<string>((ok, fail) => {
      const timer = setTimeout(() => fail(new Error('Chrome did not start in 20 seconds')), 20000)
      let seen = ''
      chrome.stderr!.on('data', (d: Buffer) => {
        seen += d.toString()
        const m = /DevTools listening on (ws:\/\/[^\s]+)/.exec(seen)
        if (m) { clearTimeout(timer); ok(m[1]) }
      })
    })
    const targets = await (await fetch(`http://127.0.0.1:${new URL(devtools).port}/json/list`)).json() as { type: string; webSocketDebuggerUrl: string }[]
    const ws = new WebSocket(targets.find((t) => t.type === 'page')!.webSocketDebuggerUrl)
    await new Promise((ok, fail) => { ws.onopen = ok; ws.onerror = fail })
    let nextId = 1
    const waiting = new Map<number, (m: any) => void>()
    let onFrame: ((p: any) => void) | undefined
    ws.onmessage = (ev) => {
      const m = JSON.parse(String(ev.data))
      if (m.id !== undefined) { waiting.get(m.id)?.(m); waiting.delete(m.id); return }
      if (m.method === 'Page.screencastFrame') {
        onFrame?.(m.params)
        call('Page.screencastFrameAck', { sessionId: m.params.sessionId }).catch(() => {})
      }
    }
    function call(method: string, params: object = {}): Promise<any> {
      const id = nextId++
      return new Promise((ok, fail) => {
        waiting.set(id, (m) => (m.error ? fail(new Error(`${method}: ${m.error.message}`)) : ok(m.result)))
        ws.send(JSON.stringify({ id, method, params }))
      })
    }
    async function js<T = any>(expression: string): Promise<T> {
      const r = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
      if (r.exceptionDetails) throw new Error(`in the page: ${r.exceptionDetails.exception?.description ?? r.exceptionDetails.text}`)
      return r.result.value as T
    }
    const wait = (ms: number): Promise<void> => new Promise((ok) => setTimeout(ok, ms))
    const q = (sel: string): string => `document.querySelector(${JSON.stringify(sel)})`
    async function until(expr: string, ms = 10000): Promise<void> {
      const stop = Date.now() + ms
      while (Date.now() < stop) { if (await js<boolean>(`!!(${expr})`)) return; await wait(50) }
      throw new Error(`timed out waiting for: ${expr}`)
    }
    async function point(sel: string): Promise<void> {
      await until(q(sel))
      await js(`${q(sel)}.scrollIntoView({ behavior: 'smooth', block: 'center' })`)
      await wait(600)
      await js(CURSOR)
      await js(`(() => { const r = ${q(sel)}.getBoundingClientRect(); const c = document.getElementById('wt-cursor')
        c.style.left = (r.left + Math.min(r.width / 2, 120)) + 'px'; c.style.top = (r.top + r.height / 2) + 'px' })()`)
      await wait(750)
    }
    async function press(sel: string): Promise<void> {
      await point(sel)
      await js(`document.getElementById('wt-cursor').classList.add('down')`)
      await wait(150)
      await js(`${q(sel)}.click(); document.getElementById('wt-cursor')?.classList.remove('down')`)
    }
    async function load(url: string): Promise<void> {
      await call('Page.navigate', { url })
      await until(`document.readyState === 'complete'`)
      await wait(400)
      await js(CURSOR)
    }

    // Headless Chrome cannot film its own print preview, so print to PDF, turn the first pages into
    // pictures with pdftoppm, and lay them side by side over the page while the camera keeps rolling
    async function showPrintedPages(count: number, hold: number): Promise<void> {
      const tmp = mkdtempSync(join(tmpdir(), 'walkthrough-print-'))
      try {
        const pdf = await call('Page.printToPDF', { printBackground: true, preferCSSPageSize: true })
        writeFileSync(join(tmp, 'print.pdf'), Buffer.from(pdf.data, 'base64'))
        const r = spawnSync('pdftoppm', ['-png', '-r', '96', '-f', '1', '-l', String(count), join(tmp, 'print.pdf'), join(tmp, 'page')])
        if (r.error || r.status !== 0) throw new Error('printPages needs pdftoppm (poppler): brew install poppler, or apt install poppler-utils')
        const pages = readdirSync(tmp).filter((f) => f.endsWith('.png')).sort().map((f) => 'data:image/png;base64,' + readFileSync(join(tmp, f)).toString('base64'))
        await js(`(() => {
          const c = document.getElementById('wt-cursor'); if (c) c.style.visibility = 'hidden'
          const o = document.createElement('div'); o.id = 'wt-print'
          o.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:#3a3f4b;display:flex;gap:24px;align-items:center;justify-content:center;padding:24px'
          for (const src of ${JSON.stringify(pages)}) {
            const img = new Image(); img.src = src
            img.style.cssText = 'max-height:100%;max-width:' + Math.floor(90 / ${pages.length}) + '%;background:#fff;box-shadow:0 8px 30px rgba(0,0,0,.4)'
            o.append(img)
          }
          document.body.append(o)
        })()`)
        await wait(hold)
        await js(`document.getElementById('wt-print')?.remove(); const c = document.getElementById('wt-cursor'); if (c) c.style.visibility = ''`)
      } finally {
        rmSync(tmp, { recursive: true, force: true })
      }
    }

    let marks: { at: number; text: string }[] = []
    let t0 = 0
    async function step(s: Step): Promise<void> {
      if ('caption' in s) marks.push({ at: (Date.now() - t0) / 1000, text: s.caption })
      else if ('goto' in s) s.goto.startsWith('#') ? await js(`location.hash = ${JSON.stringify(s.goto)}`) : await load(new URL(s.goto, base).href)
      else if ('click' in s) await press(s.click)
      else if ('point' in s) await point(s.point)
      else if ('type' in s) {
        const [sel, text] = s.type
        await press(sel)
        // typing replaces what is there unless the step says append, so a script never needs a clear first
        await js(`(() => { const e = ${q(sel)}; e.focus(); if (${!s.append}) { e.value = ''; e.dispatchEvent(new Event('input', { bubbles: true })) } })()`)
        for (const ch of String(text)) { await call('Input.insertText', { text: ch }); await wait(s.delay ?? 110) }
        await js(`${q(sel)}.dispatchEvent(new Event('change', { bubbles: true }))`)
      } else if ('clear' in s) {
        await press(s.clear)
        await js(`(() => { const e = ${q(s.clear)}; e.value = ''; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })) })()`)
      } else if ('select' in s) {
        const [sel, value] = s.select
        await press(sel)
        await js(`(() => { const e = ${q(sel)}; e.value = ${JSON.stringify(value)}; e.dispatchEvent(new Event('change', { bubbles: true })) })()`)
      } else if ('upload' in s) {
        const [sel, file] = s.upload
        await point(sel)
        const doc = await call('DOM.getDocument')
        const node = await call('DOM.querySelector', { nodeId: doc.root.nodeId, selector: sel })
        await call('DOM.setFileInputFiles', { nodeId: node.nodeId, files: [resolve(here, file)] })
        await js(`${q(sel)}.dispatchEvent(new Event('change', { bubbles: true }))`)
      } else if ('wait' in s) await wait(s.wait)
      else if ('waitFor' in s) await until(s.waitFor, s.timeout)
      else if ('eval' in s) await js(s.eval)
      else if ('viewport' in s) {
        const [w, h] = s.viewport
        await call('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: !!s.mobile })
        await wait(300)
      } else if ('media' in s) await call('Emulation.setEmulatedMedia', { media: s.media === 'screen' ? '' : s.media })
      else if ('printPages' in s) await showPrintedPages(s.printPages === true ? 2 : Number(s.printPages), s.hold ?? 4000)
      else throw new Error(`unknown step: ${JSON.stringify(s)}`)
    }

    await call('Page.enable')
    await call('DOM.enable')
    await call('Emulation.setDeviceMetricsOverride', { width: view[0], height: view[1], deviceScaleFactor: 1, mobile: false })
    await load(base)

    const recorded: Recorded[] = []
    const metaPath = join(out, 'scenes.json')
    const previous: Recorded[] = existsSync(metaPath) ? JSON.parse(readFileSync(metaPath, 'utf8')) : []
    for (const [k, scene] of config.scenes.entries()) {
      const n = k + 1
      if (scene.reload) await load(base)
      for (const s of scene.before ?? []) await step(s)
      if (only && !only.includes(n)) {
        // Skipped scenes still play their steps off camera, so later scenes start from the same page
        for (const s of scene.steps) if (!('wait' in s) && !('caption' in s)) await step(s)
        if (!previous[k]) throw new Error(`scene ${n} has never been recorded; record it once without --scenes`)
        recorded.push(previous[k])
        continue
      }
      const frames: { t: number; data: string }[] = []
      onFrame = (p) => frames.push({ t: p.metadata.timestamp, data: p.data })
      await call('Page.startScreencast', { format: 'jpeg', quality: 85, everyNthFrame: 1 })
      await wait(300)
      t0 = Date.now()
      marks = []
      for (const s of scene.steps) await step(s)
      await wait(400)
      const end = Date.now() / 1000
      await call('Page.stopScreencast')
      onFrame = undefined
      if (!frames.length) throw new Error(`scene ${n} captured no frames`)
      const startAt = t0 / 1000
      const kept = frames.filter((f) => f.t >= startAt - 0.5)
      const dir = mkdtempSync(join(tmpdir(), `walkthrough-${n}-`))
      const list: string[] = []
      kept.forEach((f, i) => {
        const file = join(dir, `${String(i).padStart(5, '0')}.jpg`)
        writeFileSync(file, Buffer.from(f.data, 'base64'))
        list.push(`file '${file}'`, `duration ${Math.max(0.001, (kept[i + 1]?.t ?? end) - Math.max(f.t, startAt))}`)
      })
      list.push(list.at(-2)!)
      writeFileSync(join(dir, 'list.txt'), list.join('\n'))
      const [vw, vh] = view
      const pad = `scale=${vw}:${vh}:force_original_aspect_ratio=decrease,pad=${vw}:${vh}:(ow-iw)/2:(oh-ih)/2:color=${(config.theme?.ground ?? '#1d2330').replace('#', '0x')}`
      const ff = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', join(dir, 'list.txt'), '-vf', pad, '-r', '30', '-g', '30', '-keyint_min', '30', '-movflags', '+faststart', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '23', join(out, 'assets', `scene-${n}.mp4`)], { stdio: 'inherit' })
      rmSync(dir, { recursive: true, force: true })
      if (ff.status !== 0) throw new Error(`ffmpeg failed on scene ${n}`)
      const duration = end - startAt
      recorded.push({ title: scene.title, duration, captions: marks })
      console.log(`scene ${n}: ${kept.length} frames, ${duration.toFixed(1)} s, ${marks.length} caption(s)`)
    }
    ws.close()

    writeFileSync(metaPath, JSON.stringify(recorded, null, 1))
    recorded.forEach((s, k) => writeFileSync(join(out, 'compositions', `s${k + 1}.html`), sceneHtml(k + 1, recorded.length, s, view)))
    writeFileSync(join(out, 'index.html'), indexHtml(recorded, config.theme))
    writeFileSync(join(out, 'hyperframes.json'), JSON.stringify({ paths: { blocks: 'compositions', components: 'compositions/components', assets: 'assets' }, media: { autoProxy: true } }, null, 2))
    writeFileSync(join(out, 'meta.json'), JSON.stringify({ id: 'walkthrough', name: config.title ?? 'walkthrough' }, null, 2))
    console.log(`video project: ${out}`)
    const appDir = resolve(here, config.start?.cwd ?? '.')
    const dirty = spawnSync('git', ['status', '--porcelain', '--', '.'], { cwd: appDir, encoding: 'utf8' })
    const changed = dirty.status === 0 ? dirty.stdout.split('\n').filter((l) => l && !/(^|[ /])video\//.test(l)).length : 0
    if (changed) console.log(`note: recorded with uncommitted changes in ${changed} file(s) under ${appDir}; the video shows them`)
  } finally {
    if (app?.pid) try { process.kill(-app.pid, 'SIGTERM') } catch { /* already gone */ }
    const gone = new Promise((ok) => chrome.once('exit', ok))
    chrome.kill('SIGKILL')
    await gone
    // Chrome's helper processes outlive the main one for a moment and keep writing the profile
    try { rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 }) } catch { /* a temp folder; the OS clears it */ }
  }

  if (args.includes('--render')) {
    const npx = (cmd: string[]): number | null => spawnSync('npx', ['--yes', HYPERFRAMES, ...cmd], { cwd: out, stdio: 'inherit' }).status
    if (npx(['check']) !== 0) throw new Error('hyperframes check failed; see above')
    if (npx(['render', '--workers', '1', '--quality', 'draft', '-o', 'renders/walkthrough.mp4']) !== 0) throw new Error('render failed')
    console.log(`video: ${join(out, 'renders', 'walkthrough.mp4')}`)
  }
}

await main()
