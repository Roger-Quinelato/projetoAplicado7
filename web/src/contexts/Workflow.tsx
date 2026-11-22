import { useEffect, useReducer, useRef, useState } from 'react'
import type { ApiResult, Process, Task, TaskState } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, dateTime, text,
  useActions, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

const PROCESS_TYPES: Record<string, string> = {
  ONBOARDING: 'Preparação de retirada',
  TICKET_RESOLUTION: 'Resolução de chamado',
  RETURN: 'Devolução',
}
const TASK_TYPE_OPTIONS = Object.entries(PROCESS_TYPES).map(([value, label]) => ({ value, label }))
const typeLabel = (type: string) => PROCESS_TYPES[type] ?? type
const CLOSED = new Set(['COMPLETED', 'CANCELLED'])
const processLabel = (p: Process) => `${PROCESS_TYPES[p.processType] ?? p.processType} · ${p.processId.slice(0, 8)}`
const ACTIVE_TASK = new Set(['OPEN', 'IN_PROGRESS'])
const sameTitle = (a: string, b: string) => a.trim().toLocaleLowerCase('pt-BR') === b.trim().toLocaleLowerCase('pt-BR')

export default function Workflow() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [processId, setProcessId] = useState('')
  const [reassigning, setReassigning] = useState<Task | null>(null)
  // Processo escolhido no formulário; sem escolha própria, acompanha o filtro da tabela de tarefas.
  const [picked, setPicked] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const panel = useRef<HTMLDivElement>(null)
  const taskList = useRef<HTMLDivElement>(null)
  // O painel fica no topo; ao clicar em Reatribuir no fim da tabela, leva a tela até ele.
  const smooth = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' as const : 'smooth' as const
  // Ao escolher Ver tarefas no quadro de processos, leva a tela até a lista de tarefas daquele processo.
  useEffect(() => { if (processId) taskList.current?.scrollIntoView({ block: 'start', behavior: smooth() }) }, [processId])
  useEffect(() => { if (reassigning) panel.current?.scrollIntoView({ block: 'start', behavior: smooth() }) }, [reassigning])

  const processes = useResource(a => a.listProcesses(), [version])
  const tasks = useResource(a => a.listTasks(processId || undefined), [processId, version])
  const allTasks = useResource(a => a.listTasks(), [version])
  const processOf = (id: string) => processes.data?.find(p => p.processId === id)
  const openProcesses = (processes.data ?? []).filter(p => !CLOSED.has(p.state))
  const selected = processId ? processOf(processId) : undefined
  const formProcess = picked ?? (selected && !CLOSED.has(selected.state) ? processId : '')
  // Tarefas do processo escolhido no formulário, para avisar sobre título repetido antes de criar.
  const formTasks = useResource(a => formProcess ? a.listTasks(formProcess) : Promise.resolve({ data: [] } as unknown as ApiResult<Task[]>), [formProcess, version])
  const repeated = title.trim() ? (formTasks.data ?? []).find(t => ACTIVE_TASK.has(t.state) && sameTitle(t.title, title)) : undefined
  const filterProcess = (id: string) => { setProcessId(id); setPicked(null) }

  function change(task: Task, state: TaskState, label: string, done: string) {
    void run(label, () => api.changeTask(task.taskId, { state }), () => done).then(r => { if (r) refresh() })
  }

  return <>
    <PageIntro>Aqui você acompanha os processos e as tarefas de cada um, como a preparação da retirada e a resolução de chamados. Os processos nascem quando você ativa uma reserva ou abre um chamado e clica em Atualizar processos. Escolha um processo para criar tarefas e marcar cada uma como iniciada, concluída ou cancelada.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two" ref={panel}>
      <Card title="Abrir operação">
        <ActionForm submit="Criar tarefa" busy={busy} label="Criar tarefa"
          // O processo é controlado pelo estado; a limpeza só zera o título e preserva o processo e o responsável.
          reset={form => { (form.elements.namedItem('title') as HTMLInputElement).value = '' }}
          onSubmit={async f => {
            const result = await run('Criação da tarefa', () => api.createTask({ processId: text(f, 'processId'), title: text(f, 'title'), owner: text(f, 'owner'), ...(text(f, 'taskType') ? { taskType: text(f, 'taskType') } : {}) }),
              () => 'Tarefa criada. Use Iniciar ou Concluir na lista de tarefas.')
            if (result) { setTitle(''); refresh() }
            return result !== null
          }}>
          <SelectField name="processId" label="Chamado" value={formProcess} onChange={setPicked}
            options={openProcesses.map(p => ({ value: p.processId, label: processLabel(p) }))}
            placeholder={processes.status === 'loading' ? 'Carregando…' : openProcesses.length ? 'Selecione' : 'Nenhum processo em andamento'}
            hint="Cada processo pode ter várias tarefas. Escolha a qual processo esta tarefa pertence." />
          <SelectField name="taskType" label="Tipo da tarefa" options={TASK_TYPE_OPTIONS} placeholder="Selecione"
            hint="Escolha o tipo desta tarefa, como Devolução para tarefas de devolução do veículo." />
          <Field name="title" label="Título da tarefa" placeholder="Ex.: Vistoriar veículo" onChange={setTitle} />
          {repeated && <div className="notice warn" role="status">
            <div>
              <strong>Já existe uma tarefa “{repeated.title}” aberta neste processo.</strong>
              <p>Ela está {repeated.state === 'IN_PROGRESS' ? 'em andamento' : 'aberta'} e o responsável é {repeated.owner}. Você pode criar outra, mas confira se não é repetida.</p>
            </div>
          </div>}
          <Field name="owner" label="Responsável" placeholder="Ex.: Oficina" />
        </ActionForm>
      </Card>

      {reassigning ? <Card title={`Reatribuir tarefa · ${reassigning.title}`}>
        <ActionForm key={reassigning.taskId} submit="Salvar responsável" busy={busy} label="Reatribuir tarefa" onSubmit={async f => {
          const result = await run('Troca de responsável', () => api.changeTask(reassigning.taskId, { state: reassigning.state, owner: text(f, 'owner') }), () => 'Responsável da tarefa atualizado.')
          if (result) { setReassigning(null); refresh() }
          return result !== null
        }}>
          <Field name="owner" label="Novo responsável" defaultValue={reassigning.owner} />
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setReassigning(null)}>Voltar</button>
      </Card> : <Card title="Quando um processo começa">
        <ul className="steps">
          <li>Ao ativar uma reserva, começa a <strong>preparação da retirada</strong>, com prazo de 72 horas.</li>
          <li>Ao abrir um chamado, começa a <strong>resolução do chamado</strong>, com o prazo do contrato.</li>
          <li>Ao resolver o chamado ou encerrar o contrato, o processo correspondente é concluído.</li>
          <li>Depois de cada uma dessas ações, clique em Atualizar processos.</li>
        </ul>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>}
    </div>

    <Card title="Operações Abertas">
      <ResourceView resource={processes} label="processos" empty="Nenhum processo ainda. Ative uma reserva ou abra um chamado e clique em Atualizar processos.">
        {all => {
          // Só operações em aberto ou em andamento; as concluídas ou canceladas vão para o Histórico de Operações.
          const rows = all.filter(r => !CLOSED.has(r.state))
          return rows.length === 0 ? <p>Nenhuma operação em aberto ou em andamento.</p> : <Table caption="Operações Abertas" rows={rows} rowKey={r => r.processId} columns={[
          { key: 'task', label: 'Tarefa', render: r => {
            const titles = (allTasks.data ?? []).filter(t => t.processId === r.processId).map(t => t.title)
            return titles.length ? titles.join(', ') : '—'
          } },
          { key: 'type', label: 'Tipo', render: r => {
            // O tipo é de cada tarefa; processo sem tarefas mostra o próprio tipo.
            const types = [...new Set((allTasks.data ?? []).filter(t => t.processId === r.processId).map(t => t.taskType ?? r.processType))]
            return (types.length ? types : [r.processType]).map(typeLabel).join(', ')
          } },
          { key: 'state', label: 'Estado', render: r => <Status value={r.state} /> },
          { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
          { key: 'actions', label: '', render: r => <button type="button" className="inline" aria-pressed={processId === r.processId}
            onClick={() => filterProcess(processId === r.processId ? '' : r.processId)}>{processId === r.processId ? 'Mostrar todas as tarefas' : 'Ver tarefas'}</button> },
        ]} />
        }}
      </ResourceView>
    </Card>

    <div ref={taskList}>
    <Card title={selected ? 'Detalhes' : 'Histórico de Operações'}
      aside={processId && <button type="button" className="secondary small" onClick={() => filterProcess('')}>Mostrar todas</button>}>
      <ResourceView resource={tasks} label="tarefas" empty={selected ? 'Nenhuma tarefa para este filtro.' : 'Nenhuma operação concluída ou cancelada ainda.'}>
        {all => {
          // Sem processo escolhido, o histórico traz só o que terminou (concluído ou cancelado); Ver tarefas mostra todas as do processo.
          const rows = selected ? all : all.filter(t => t.state === 'DONE' || t.state === 'CANCELLED')
          return rows.length === 0 ? <p>Nenhuma operação concluída ou cancelada ainda.</p> : <Table caption={selected ? 'Tarefas' : 'Histórico de Operações'} rows={rows} rowKey={r => r.taskId} columns={[
          { key: 'title', label: 'Tarefa', render: r => r.title },
          { key: 'process', label: 'Processo', render: r => { const p = processOf(r.processId); return p ? processLabel(p) : <Id value={r.processId} /> } },
          // Em Detalhes, o estado é o do processo, o mesmo do quadro Processos.
          { key: 'state', label: 'Estado', render: r => <Status value={selected ? selected.state : r.state} /> },
          { key: 'owner', label: 'Responsável', render: r => r.owner },
          { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
          { key: 'actions', label: 'Ações', render: r => {
            const p = processOf(r.processId)
            if ((p && CLOSED.has(p.state)) || r.state === 'DONE' || r.state === 'CANCELLED') return '—'
            return <div className="row-actions">
              {r.state === 'OPEN' && <button type="button" className="inline" disabled={busy} onClick={() => change(r, 'IN_PROGRESS', 'Início da tarefa', 'Tarefa iniciada.')}>Iniciar</button>}
              <button type="button" className="inline" disabled={busy} onClick={() => change(r, 'DONE', 'Conclusão da tarefa', 'Tarefa concluída.')}>Concluir</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => { setReassigning(r); clear() }}>Reatribuir…</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => { if (window.confirm(`Cancelar a tarefa “${r.title}”?`)) change(r, 'CANCELLED', 'Cancelamento da tarefa', 'Tarefa cancelada.') }}>Cancelar</button>
            </div>
          } },
        ]} />
        }}
      </ResourceView>
    </Card>
    </div>
  </>
}
