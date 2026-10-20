import { useReducer, useState } from 'react'
import type { Process, Task, TaskState } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, MoreMenu, PageIntro, Panel, ResourceView, SelectField, Stack, Status, Table, dateTime, text,
  useActions, useConfirm, useResource, useSession,
} from '../ui'

const PROCESS_TYPES: Record<string, { label: string, origin: string }> = {
  ONBOARDING: { label: 'Preparação de retirada', origin: 'Contrato' },
  TICKET_RESOLUTION: { label: 'Resolução de chamado', origin: 'Chamado' },
}
const CLOSED = new Set(['COMPLETED', 'CANCELLED'])
const processLabel = (p: Process) => `${PROCESS_TYPES[p.processType]?.label ?? p.processType} · ${p.processId.slice(0, 8)}`

type PanelState = { kind: 'create' } | { kind: 'reassign', task: Task } | null

export default function Workflow() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const { ask, dialog } = useConfirm()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [processId, setProcessId] = useState('')
  const [panel, setPanel] = useState<PanelState>(null)

  const processes = useResource(a => a.listProcesses(), [version])
  const tasks = useResource(a => a.listTasks(processId || undefined), [processId, version])
  const processOf = (id: string) => processes.data?.find(p => p.processId === id)
  const openProcesses = (processes.data ?? []).filter(p => !CLOSED.has(p.state))
  const selected = processId ? processOf(processId) : undefined

  const MESSAGES: Record<TaskState, string> = { OPEN: 'reaberta', IN_PROGRESS: 'iniciada', DONE: 'concluída', CANCELLED: 'cancelada' }
  function change(task: Task, state: TaskState, label: string) {
    void run(label, () => api.changeTask(task.taskId, { state }), undefined, {
      success: t => `Tarefa “${t.title}” ${MESSAGES[state]}.`, failure: `Não foi possível atualizar a tarefa “${task.title}”.`,
    }).then(r => { if (r) refresh() })
  }

  async function cancel(task: Task) {
    const ok = await ask({ title: `Cancelar a tarefa “${task.title}”?`, body: 'A tarefa sai da lista de pendências do processo. O histórico fica preservado.', confirm: 'Cancelar tarefa', cancel: 'Manter tarefa' })
    if (ok) change(task, 'CANCELLED', 'Cancelamento de tarefa')
  }

  return <>
    <PageIntro>Processos nascem dos eventos de contrato ativado e de chamado aberto, depois do despacho na barra do topo. Aqui você acompanha os processos e executa as tarefas.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    {dialog}

    <Card title="Processos">
      <ResourceView resource={processes} label="processos" empty="Nenhum processo ainda. Ative um contrato ou abra um chamado e despache os eventos na barra do topo.">
        {rows => <Table caption="Processos" rows={rows} rowKey={r => r.processId} rowClass={r => processId === r.processId ? 'selected' : undefined} columns={[
          { key: 'type', label: 'Tipo', render: r => PROCESS_TYPES[r.processType]?.label ?? r.processType },
          { key: 'id', label: 'Processo', render: r => <Id value={r.processId} /> },
          { key: 'ref', label: 'Origem', render: r => <span className="row-actions">{PROCESS_TYPES[r.processType]?.origin ?? 'Referência'} <Id value={r.referenceId} /></span> },
          { key: 'state', label: 'Estado', render: r => <Status value={r.state} /> },
          { key: 'owner', label: 'Responsável', render: r => r.owner },
          { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
          { key: 'actions', label: 'Ações', render: r => <button type="button" className={`inline${CLOSED.has(r.state) ? ' quiet' : ''}`} aria-pressed={processId === r.processId}
            onClick={() => setProcessId(processId === r.processId ? '' : r.processId)}>{processId === r.processId ? 'Mostrar todas' : 'Ver tarefas'}</button> },
        ]} />}
      </ResourceView>
    </Card>

    <Card title={selected ? `Tarefas · ${processLabel(selected)}` : 'Tarefas'} aside={<div className="head-actions">
      <div className="inline-filter">
        <label htmlFor="task-process">Processo</label>
        <select id="task-process" value={processId} onChange={e => setProcessId(e.target.value)}>
          <option value="">Todos</option>
          {(processes.data ?? []).map(p => <option key={p.processId} value={p.processId}>{processLabel(p)}</option>)}
        </select>
      </div>
      <button type="button" onClick={() => { setPanel({ kind: 'create' }); clear() }}>Criar tarefa</button>
    </div>}>
      <ResourceView resource={tasks} label="tarefas" empty="Nenhuma tarefa para este filtro.">
        {rows => <Table caption="Tarefas" rows={rows} rowKey={r => r.taskId} columns={[
          { key: 'title', label: 'Tarefa', render: r => { const p = processOf(r.processId); return <Stack main={r.title} sub={p ? processLabel(p) : r.processId.slice(0, 8)} /> } },
          { key: 'state', label: 'Estado', render: r => <Status value={r.state} /> },
          { key: 'owner', label: 'Responsável', render: r => r.owner },
          { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
          { key: 'actions', label: 'Ações', render: r => {
            const p = processOf(r.processId)
            if ((p && CLOSED.has(p.state)) || r.state === 'DONE' || r.state === 'CANCELLED') return '—'
            return <div className="row-actions">
              {r.state === 'OPEN' && <button type="button" className="inline" disabled={busy} onClick={() => change(r, 'IN_PROGRESS', 'Início de tarefa')}>Iniciar</button>}
              <button type="button" className="inline" disabled={busy} onClick={() => change(r, 'DONE', 'Conclusão de tarefa')}>Concluir</button>
              <MoreMenu label={`tarefa ${r.title}`} items={[
                { label: 'Reatribuir…', disabled: busy, onSelect: () => { setPanel({ kind: 'reassign', task: r }); clear() } },
                { label: 'Cancelar tarefa…', danger: true, disabled: busy, onSelect: () => void cancel(r) },
              ]} />
            </div>
          } },
        ]} />}
      </ResourceView>
    </Card>

    {panel && <div className="grid two">
      {panel.kind === 'create' && <Panel title="Criar tarefa" onClose={() => setPanel(null)}>
        <ActionForm key={processId} submit="Criar tarefa" busy={busy} label="Criar tarefa" onSubmit={async f => {
          const title = text(f, 'title')
          const result = await run('Criação de tarefa', () => api.createTask({ processId: text(f, 'processId'), title, owner: text(f, 'owner') }), undefined,
            { success: () => `Tarefa “${title}” criada.`, failure: 'Não foi possível criar a tarefa.' })
          if (result) refresh()
          return result !== null
        }}>
          <SelectField name="processId" label="Processo em andamento" defaultValue={selected && !CLOSED.has(selected.state) ? processId : ''}
            options={openProcesses.map(p => ({ value: p.processId, label: processLabel(p) }))}
            placeholder={processes.status === 'loading' ? 'Carregando…' : openProcesses.length ? 'Selecione' : 'Nenhum processo em andamento'} />
          <div className="form-grid">
            <Field name="title" label="Título da tarefa" placeholder="Ex.: Vistoriar veículo" />
            <Field name="owner" label="Responsável" defaultValue="operations" hint="Equipe ou função, sem e-mail ou telefone." />
          </div>
        </ActionForm>
      </Panel>}

      {panel.kind === 'reassign' && <Panel title={`Reatribuir tarefa · ${panel.task.title}`} onClose={() => setPanel(null)}>
        <ActionForm key={panel.task.taskId} submit="Salvar responsável" busy={busy} label="Reatribuir tarefa" onSubmit={async f => {
          const owner = text(f, 'owner')
          const result = await run('Reatribuição de tarefa', () => api.changeTask(panel.task.taskId, { state: panel.task.state, owner }), undefined,
            { success: t => `Tarefa “${t.title}” atribuída a ${owner}.`, failure: 'Não foi possível reatribuir a tarefa.' })
          if (result) { setPanel(null); refresh() }
          return result !== null
        }}>
          <Field name="owner" label="Novo responsável" defaultValue={panel.task.owner} hint="Equipe ou função, sem e-mail ou telefone." />
        </ActionForm>
      </Panel>}

      <Card title="Eventos que iniciam processos">
        <ol className="flow-steps">
          <li><span><code>ContractActivated.v1</code> cria a preparação de retirada, com prazo de 72 h.</span></li>
          <li><span><code>TicketOpened.v1</code> cria a resolução de chamado, com o prazo do SLA.</span></li>
          <li><span><code>TicketResolved.v1</code> e <code>ContractClosed.v1</code> concluem o processo correspondente.</span></li>
        </ol>
      </Card>
    </div>}
  </>
}
