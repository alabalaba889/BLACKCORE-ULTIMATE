# BLACKCORE ULTIMATE — roadmap

Este documento distingue recursos implementados, protótipos e trabalho futuro. Testes automatizados não substituem testes no PC real.

## Etapa 1 — base local
- Implementado: aplicação Tkinter existente, launcher, registro de eventos e confirmação antes das ações locais sensíveis.
- Implementado: módulos para métricas somente leitura, autorização, backups e validação de manifestos.
- Implementado: testes automatizados em GitHub Actions para Windows e Linux.
- Falta: modularização adicional da aplicação principal, testes de instalação limpa e diagnósticos de configuração.

## Etapa 2 — controles do Windows (parcial)
- Implementado: abrir Bloco de Notas/Calculadora, movimento/clique do mouse por coordenadas e lista permitida de atalhos, sempre com confirmação.
- Implementado: digitação de texto após confirmação e contagem regressiva visível.
- Falta: catálogo maior de ações seguras, controles de processos com lista permitida, cancelamento global e testes no PC do usuário.
- Não há elevação de privilégios silenciosa.

## Etapa 3 — monitoramento (parcial)
- Implementado na interface: CPU, RAM, uso do disco e histórico compacto de CPU/RAM/disco.
- Implementado: amostrador de velocidade de rede baseado em contadores opcionais de psutil.
- Implementado como helpers ainda não integrados à tela: snapshot limitado de processos e telemetria NVIDIA opcional via nvidia-smi com timeout.
- Falta: gráficos históricos, métricas por processo na interface, GPU/jogos com provedores documentados e alertas configuráveis. Hardware sem suporte deve ser mostrado como indisponível.

## Etapa 4 — IA híbrida (chat inicial integrado)
- Implementado: janela Workbench com chat assíncrono para Ollama local ou API compatível com OpenAI.
- Implementado: limites de entrada/saída, timeout, validação do endpoint, erros sanitizados e respostas apenas em texto; a resposta da IA nunca é executada.
- Falta: cofre de credenciais do Windows, assistente de configuração, persistência de conversas/projetos, anexos, cancelamento/repetição e fluxo de aprovação para ferramentas futuras.
- Nunca guardar chaves em arquivos públicos ou no código do cliente.

## Etapa 5 — Roblox Studio Lab (inspeção integrada)
- Implementado: seleção de pasta pela interface, varredura somente leitura de arquivos .lua/.luau com limites de tamanho/quantidade e regras heurísticas.
- Implementado em biblioteca: prévia de diff unificado que não grava alterações.
- Falta: parser/tipagem Luau mais completo, plano de testes, diff na interface, plugin oficial de integração com Studio, backup antes de aplicar e aplicação controlada seguida de testes.
- Nenhum script do projeto é executado pelo Lab; não é um executor de exploits ou cheats.

## Etapa 6 — plugins e recuperação (parcial)
- Implementado: cadastro de manifesto JSON com aprovação explícita, zero permissões concedidas por padrão e plugins desativados por padrão.
- Importante: ativar um plugin só altera metadados; código externo não é carregado nem executado.
- Implementado: backup versionado de arquivos, hash SHA-256, confirmação de restauração e substituição atômica.
- Implementado na interface: criar/restaurar backup de arquivo e cadastrar manifesto de plugin.
- Falta: sandbox real de processos, catálogo de fontes confiáveis, gestão visual de permissões, histórico de recuperação e backup/restauração de projetos inteiros.
- O hash ajuda a detectar divergência em relação aos metadados guardados, mas não é assinatura digital; mantenha backup e metadados protegidos.

## Etapa 7 — Android e controle remoto (primitivas somente)
- Implementado: código de pareamento de uso único, permissões mínimas, expiração, revogação, rate limit e auditoria sem registrar tokens.
- Não implementado: app Android, streaming real da tela, execução remota de mouse/teclado ou serviço de rede.
- Falta: transporte autenticado e criptografado, VPN privada para acesso externo, consentimento visível no desktop, gestão de dispositivos e testes de ponta a ponta.
- Não expor uma porta de controle diretamente à internet.

## Validação e entrega
- Cada alteração dispara o workflow de compilação e testes unitários; confira a execução mais recente antes de afirmar que passou.
- Ainda faltam testes reais de interface, provedor de IA, GPU, Roblox Studio, Android e instalação limpa no Windows 10/11.
- Falta empacotamento portátil/instalador com runtime, atualizador seguro, desinstalação limpa, assinatura e estratégia de rollback.
- A branch de trabalho não é automaticamente a branch main; integrar e publicar exige revisão e validação próprias.
