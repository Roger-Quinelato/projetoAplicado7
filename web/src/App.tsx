import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { asApiError, createApi, errorHeadline, type ApiError } from './api'
import { SessionContext, type Session } from './ui'
import Overview from './contexts/Overview'
import Crm from './contexts/Crm'
import Contracts from './contexts/Contracts'
import Finance from './contexts/Finance'
import Support from './contexts/Support'
import Workflow from './contexts/Workflow'

const TOKEN_KEY = 'archcorp-demo-token'

const ROUTES = [
  { path: '/', label: 'Visão geral', eyebrow: 'INTEGRAÇÃO E OPERAÇÃO' },
  { path: '/crm', label: 'CRM', eyebrow: 'CONTEXTO 1 · CLIENTES' },
  { path: '/reservas', label: 'Reservas e contratos', eyebrow: 'CONTEXTO 2 · CONTRACTS' },
  { path: '/financeiro', label: 'Financeiro', eyebrow: 'CONTEXTO 3 · FINANCE' },
  { path: '/atendimento', label: 'Atendimento', eyebrow: 'CONTEXTO 4 · SUPPORT' },
  { path: '/workflow', label: 'Workflow', eyebrow: 'CONTEXTO 5 · PROCESSOS' },
] as const
type RoutePath = typeof ROUTES[number]['path']

function parseHash(): { path: RoutePath, params: URLSearchParams, raw: string } {
  const raw = window.location.hash.replace(/^#/, '') || '/'
  const [pathPart, query = ''] = raw.split('?')
  const route = ROUTES.find(r => r.path === pathPart)
  return { path: route ? route.path : '/', params: new URLSearchParams(query), raw }
}

function readStoredToken(): string {
  try { return sessionStorage.getItem(TOKEN_KEY) ?? '' } catch { return '' }
}
function storeToken(token: string) {
  try { if (token) sessionStorage.setItem(TOKEN_KEY, token); else sessionStorage.removeItem(TOKEN_KEY) } catch { /* armazenamento indisponível: a sessão vale só nesta aba */ }
}

type GateState = { status: 'idle' } | { status: 'checking' } | { status: 'error', error: ApiError, message?: string }

/** Conectividade observada nas respostas da API; não é inferida da autenticação. */
type Link = { status: 'unknown' } | { status: 'up' | 'down' | 'degraded', at: Date }

function time(at: Date): string {
  return at.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function LinkStatus({ link, onCheck }: { link: Link, onCheck: () => void }) {
  const text = link.status === 'up' ? `API respondeu às ${time(link.at)}`
    : link.status === 'down' ? `Sem resposta da API às ${time(link.at)}`
    : link.status === 'degraded' ? `API respondeu às ${time(link.at)}, mas o banco está indisponível`
    : 'Conexão com a API ainda não observada'
  // O horário muda a cada resposta; o leitor de tela só é avisado quando o estado muda.
  const announced = { unknown: 'não observada', up: 'respondendo', down: 'sem resposta', degraded: 'banco indisponível' }[link.status]
  return <div className="link-status">
    <span className={`link-dot ${link.status}`} aria-hidden="true" />
    <span className="link-text">{text}</span>
    <span className="sr-only" role="status">Conexão com a API: {announced}</span>
    <button type="button" onClick={onCheck}>Verificar</button>
  </div>
}

export default function App() {
  const [token, setToken] = useState('')
  const [gate, setGate] = useState<GateState>({ status: 'idle' })
  const [route, setRoute] = useState(parseHash)
  const [link, setLink] = useState<Link>({ status: 'unknown' })
  const reach = useCallback((reachable: boolean) => setLink({ status: reachable ? 'up' : 'down', at: new Date() }), [])
  const heading = useRef<HTMLHeadingElement>(null)
  const firstRender = useRef(true)

  /** A credencial é válida quando a API responde 200 ou 403 (autenticado, porém sem papel admin). */
  const verify = useCallback(async (candidate: string) => {
    setGate({ status: 'checking' })
    try {
      await createApi(candidate, undefined, reach).demoState()
    } catch (error) {
      const apiError = asApiError(error)
      if (apiError.status !== 403) {
        storeToken('')
        setToken('')
        setGate({ status: 'error', error: apiError })
        return
      }
    }
    storeToken(candidate)
    setToken(candidate)
    setGate({ status: 'idle' })
  }, [reach])

  useEffect(() => {
    const stored = readStoredToken()
    if (stored) void verify(stored)
  }, [verify])

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return }
    heading.current?.focus()
  }, [route.raw])

  const signOut = useCallback(() => {
    storeToken('')
    setToken('')
    setGate({ status: 'idle' })
  }, [])
  const navigate = useCallback((target: string) => { window.location.hash = target }, [])
  const session = useMemo<Session | null>(() => token ? { api: createApi(token, undefined, reach), signOut, navigate } : null, [token, signOut, navigate, reach])

  if (!session) return <Gate state={gate} onSubmit={value => void verify(value)} />

  const current = ROUTES.find(r => r.path === route.path) ?? ROUTES[0]
  const profile = token.startsWith('demo-') ? `Perfil local: ${token.replace('demo-', '')}` : 'Credencial compartilhada'

  return <SessionContext.Provider value={session}>
    <a className="skip" href="#conteudo" onClick={e => { e.preventDefault(); heading.current?.focus() }}>Pular para o conteúdo</a>
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="mark" aria-hidden="true">A</div><div><strong>ArchCorp</strong><span>Integração aplicada</span></div></div>
        <p className="sidebar-title" id="nav-title">CONTEXTOS</p>
        <nav aria-labelledby="nav-title">
          {ROUTES.map(r => <a key={r.path} href={`#${r.path}`} aria-current={r.path === current.path ? 'page' : undefined}>{r.label}</a>)}
        </nav>
        <div className="side-bottom">
          <LinkStatus link={link} onCheck={() => void session.api.readiness().catch(error => {
            // Falha de rede já chegou pelo sinal de conectividade; 503 é API no ar com banco indisponível.
            if (asApiError(error).status === 503) setLink({ status: 'degraded', at: new Date() })
          })} />
          <div className="side-profile">
            <span>{profile}</span>
            <button type="button" onClick={signOut}>Sair</button>
          </div>
        </div>
      </aside>
      <main id="conteudo">
        <header className="topbar">
          <div>
            <p className="eyebrow">{current.eyebrow}</p>
            <h1 ref={heading} tabIndex={-1}>{current.label}</h1>
          </div>
          <div className="top-actions">
            <span className="profile-chip">{profile}</span>
            <a href="/docs" target="_blank" rel="noreferrer">Documentação da API<span className="sr-only"> (abre em nova aba)</span> ↗</a>
          </div>
        </header>
        <div key={route.raw}>
          {current.path === '/' && <Overview params={route.params} />}
          {current.path === '/crm' && <Crm />}
          {current.path === '/reservas' && <Contracts params={route.params} />}
          {current.path === '/financeiro' && <Finance />}
          {current.path === '/atendimento' && <Support params={route.params} />}
          {current.path === '/workflow' && <Workflow />}
        </div>
        <footer>Demonstração acadêmica ArchCorp · Dados sintéticos · Integrações externas simuladas · Sem conexão com sistemas reais da Localiza</footer>
      </main>
    </div>
  </SessionContext.Provider>
}

function Gate({ state, onSubmit }: { state: GateState, onSubmit: (token: string) => void }) {
  const [entry, setEntry] = useState(import.meta.env.DEV ? 'demo-admin' : '')
  function submit(event: FormEvent) {
    event.preventDefault()
    const value = entry.trim()
    if (value) onSubmit(value)
  }
  return <div className="gate">
    <main className="gate-card">
      <div className="mark" aria-hidden="true">A</div>
      <p className="eyebrow">ARCHCORP · AMBIENTE ACADÊMICO</p>
      <h1>Operações integradas</h1>
      <p>Entre com a credencial de demonstração para navegar pelos cinco contextos com dados sintéticos. No ambiente local, use um dos tokens de papel descritos no README; na demonstração pública, solicite a credencial ao responsável pelo projeto.</p>
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="token">Credencial de acesso</label>
          <input id="token" type="password" value={entry} onChange={e => setEntry(e.target.value)} required autoComplete="off" />
        </div>
        <button type="submit" disabled={state.status === 'checking'}>{state.status === 'checking' ? 'Validando…' : 'Acessar demonstração'}</button>
      </form>
      <div aria-live="polite">
        {state.status === 'error' && <div className="notice error" role="alert"><div>
          <strong>{errorHeadline(state.error)}</strong>
          {state.error.detail && <p>{state.error.detail}</p>}
          <p className="meta">{state.error.kind === 'network' ? 'Sem resposta do servidor' : `HTTP ${state.error.status} · código ${state.error.code}`}{state.error.correlationId && <> · Correlação: <code>{state.error.correlationId}</code></>}</p>
        </div></div>}
      </div>
      <small>Projeto conceitual; sem conexão com sistemas reais da Localiza. Use apenas dados fictícios.</small>
    </main>
  </div>
}
