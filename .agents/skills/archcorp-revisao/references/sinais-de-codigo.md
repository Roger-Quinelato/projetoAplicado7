# Sinais de código (julgamento, não regra)

Base mínima de sinais para o eixo **Padrões**, aplicada mesmo quando o repositório não documenta o assunto. Cada sinal é rotulado como possibilidade ("possível inveja de dados"), nunca como violação. Um padrão documentado em `AGENTS.md` ou ADR **prevalece**: se ele endossa algo que o sinal apontaria, suprima o sinal. Ignore o que ferramentas já verificam.

| Sinal | O que é | Correção típica |
|---|---|---|
| Nome misterioso | Função, variável ou tipo cujo nome não revela o que faz ou guarda | Renomear; se não houver nome honesto, o desenho está confuso |
| Código duplicado | A mesma forma de lógica em mais de um trecho da mudança | Extrair a forma comum e chamá-la dos dois lugares |
| Inveja de dados | Função que usa mais dados de outro objeto ou contexto que os próprios | Mover a lógica para o dono dos dados (ver fronteiras) |
| Grupo de dados | Os mesmos campos viajam sempre juntos (ex.: valor + moeda + ciclo) | Agrupar num tipo próprio |
| Obsessão por primitivos | `str`/`float` representando conceito de domínio (dinheiro, prazo, estado) | Tipo pequeno ou enum do domínio |
| Condicional repetida | O mesmo `if`/`match` sobre o mesmo tipo em vários lugares | Tabela única (ex.: transições) compartilhada |
| Cirurgia em espingarda | Uma mudança lógica força edições espalhadas em muitos arquivos | Reunir o que muda junto no mesmo módulo |
| Mudança divergente | Um arquivo alterado por vários motivos sem relação | Separar responsabilidades |
| Generalidade especulativa | Abstração, parâmetro ou gancho sem uso no aceite | Remover até existir necessidade real |
| Cadeia de mensagens | Navegação longa `a.b().c().d()` da qual o chamador depende | Esconder o caminho atrás de um método |
| Intermediário | Classe ou função que só repassa a chamada | Chamar o destino diretamente |

Adaptado da base de *code smells* da skill `code-review` de [mattpocock/skills](https://github.com/mattpocock/skills) (MIT; aviso em `docs/agentes/licencas/MIT-mattpocock-skills.txt`), que por sua vez segue Fowler, *Refactoring*, cap. 3.
