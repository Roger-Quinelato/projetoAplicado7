import { useReducer, useState } from 'react'
import type { Process, Task, TaskState } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, dateTime, text,
  useActions, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

const PROCESS_TYPES: Record<string, string> = {
  ONBOARDING: 'Preparação de retirada',
  TICKET_RESOLUTION: 'Resolução de chamado',
}
const CLOSED = new Set(['COMPLETED', 'CANCELLED'])
const processLabel = (p: Process) => `${PROCESS_TYPES[p.processType] ?? p.processType} · ${p.processId.slice(0, 8)}`

export default function Workflow() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [processId, setProcessId] = useState('')
  const [reassigning, setReassigning] = useState<Task | null>(null)

  const processes = useResource(a => a.listProcesses(), [version])
  const tasks = useResource(a => a.listTasks(processId || undefined), [processId, version])
  const processOf = (id: string) => processes.data?.find(p => p.processId === id)
  const openProcesses = (processes.data ?? []).filter(p => !CLOSED.has(p.state))
  const selected = processId ? processOf(processId) : undefined

  function change(task: Task, state: TaskState, label: string) {
    void run(label, () => api.changeTask(task.taskId, { state })).then(r => { if (r) refresh() })
  }

  return <>
    <PageIntro>Instância, tarefa, responsável, prazo e estado operacional pertencem a Workflow. Processos nascem de eventos (contrato ativado, chamado aberto) após o despacho; aqui você cria tarefas e executa as transições.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Criar tarefa" roles="operations, admin">
        <ActionForm key={processId} submit="Criar tarefa" busy={busy} label="Criar tarefa" onSubmit={async f => {
          const result = await run('Criação de tarefa', () => api.createTask({ processId: text(f, 'processId'), title: text(f, 'title'), owner: text(f, 'owner') }))
          if (result) refresh()
          return result !== null
        }}>
          <SelectField name="processId" label="Processo em andamento" defaultValue={selected && !CLOSED.has(selected.state) ? processId : ''}
            options={openProcesses.map(p => ({ value: p.processId, label: processLabel(p) }))}
            placeholder={processes.status === 'loading' ? 'Carregando…' : openProcesses.length ? 'Selecione' : 'Nenhum processo em andamento'} />
          <Field name="title" label="Título da tarefa" placeholder="Ex.: Vistoriar veículo" />
          <Field name="owner" label="Responsável" defaultValue="operations" />
        </ActionForm>
      </Card>

      {reassigning ? <Card title={`Reatribuir tarefa · ${reassigning.title}`} roles="operations, admin">
        <ActionForm key={reassigning.taskId} submit="Salvar responsável" busy={busy} label="Reatribuir tarefa" onSubmit={async f => {
          const result = await run('Reatribuição de tarefa', () => api.changeTask(reassigning.taskId, { state: reassigning.state, owner: text(f, 'owner') }))
          if (result) { setReassigning(null); refresh() }
          return result !== null
        }}>
          <Field name="owner" label="Novo responsável" defaultValue={reassigning.owner} />
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setReassigning(null)}>Voltar</button>
      </Card> : <Card title="Eventos que iniciam processos" roles="despacho: operations, admin">
        <ul className="steps">
          <li><code>ContractActivated.v1</code> → preparação de retirada (prazo de 72 h).</li>
          <li><code>TicketOpened.v1</code> → resolução de chamado (prazo = SLA do contrato).</li>
          <li><code>TicketResolved.v1</code> e <code>ContractClosed.v1</code> → concluem o processo correspondente.</li>
        </ul>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>}
    </div>

    <Card title="Processos" roles="operations, support, contracts, admin">
      <ResourceView resource={processes} label="processos" empty="Nenhum processo ainda. Ative um contrato ou abra um chamado e despache os eventos.">
        {rows => <Table caption="Processos" rows={rows} rowKey={r => r.processId} columns={[
          { key: 'type', label: 'Tipo', render: r => PROCESS_TYPES[r.processType] ?? r.processType },
          { key: 'id', label: 'Processo', render: r => <Id value={r.processId} /> },
          { key: 'ref', label: 'Referência', render: r => <Id value={r.referenceId} /> },
          { key: 'state', label: 'Estado', render: r => <Status value={r.state} /> },
          { key: 'owner', label: 'Responsável', render: r => r.owner },
          { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
          { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline" aria-pressed={processId === r.processId}
            onClick={() => setProcessId(processId === r.processId ? '' : r.processId)}>{processId === r.processId ? 'Mostrar todas as tarefas' : 'Ver tarefas'}</button> },
        ]} />}
      </ResourceView>
    </Card>

    <Card title={selected ? `Tarefas · ${processLabel(selected)}` : 'Tarefas (todos os processos)'} roles="leitura: operations, support, contracts, admin · transições: operations, admin"
      aside={processId && <button type="button" className="secondary small" onClick={() => setProcessId('')}>Mostrar todas</button>}>
      <ResourceView resource={tasks} label="tarefas" empty="Nenhuma tarefa para este filtro.">
        {rows => <Table caption="Tarefas" rows={rows} rowKey={r => r.taskId} columns={[
          { key: 'title', label: 'Tarefa', render: r => r.title },
          { key: 'process', label: 'Processo', render: r => { const p = processOf(r.processId); return p ? processLabel(p) : <Id value={r.processId} /> } },
          { key: 'state', label: 'Estado', render: r => <Status value={r.state} /> },
          { key: 'owner', label: 'Responsável', render: r => r.owner },
          { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
          { key: 'actions', label: 'Ações', render: r => {
            const p = processOf(r.processId)
            if ((p && CLOSED.has(p.state)) || r.state === 'DONE' || r.state === 'CANCELLED') return '—'
            return <div className="row-actions">
              {r.state === 'OPEN' && <button type="button" className="inline" disabled={busy} onClick={() => change(r, 'IN_PROGRESS', 'Início de tarefa')}>Iniciar</button>}
              <button type="button" className="inline" disabled={busy} onClick={() => change(r, 'DONE', 'Conclusão de tarefa')}>Concluir</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => { setReassigning(r); clear() }}>Reatribuir…</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => { if (window.confirm(`Cancelar a tarefa “${r.title}”?`)) change(r, 'CANCELLED', 'Cancelamento de tarefa') }}>Cancelar</button>
            </div>
          } },
        ]} />}
      </ResourceView>
    </Card>
  </>
}
