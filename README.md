# BLACKCORE ULTIMATE — foundation v0.2

Projeto portátil para Windows, construído por etapas. O aplicativo original foi preservado; esta branch adiciona uma base modular para monitoramento, confirmação de ações, backups, validação de plugins e testes automatizados.

## Já existe no repositório
- Interface Tkinter escura estilo terminal hacker.
- Monitoramento básico de CPU e RAM na interface original.
- Atalhos para abrir Bloco de Notas e Calculadora.
- Digitação de texto no aplicativo ativo após confirmação e contagem de 3 segundos.
- Simulações visuais reversíveis e log local.
- Métricas de disco e velocidade de rede (opcional, depende de `psutil`) na interface; aba de desempenho no Workbench com lista de processos e telemetria NVIDIA opcional.
- Controles locais de movimento e clique do mouse por coordenadas, com confirmação visível antes de cada ação.
- Camada de autorização explícita para ações sensíveis.
- Helpers de backup e restauração que exigem confirmação explícita ao restaurar.
- Backups versionados com hash SHA-256, restauração atômica e bloqueio quando a integridade não confere.
- Registro local de plugins com concessão individual de permissões; ativação é apenas metadado e não executa código.
- Primitivas de pareamento remoto com código de uso único, expiração, permissões mínimas, revogação, rate limit e auditoria sem tokens.
- Testes unitários e workflow de CI para Windows e Linux.

## Ainda não implementado
- App Android, transmissão real de tela e execução dos comandos remotos.
- Transporte de rede autenticado e criptografado para o protocolo de pareamento (as primitivas atuais não abrem portas nem criam servidor).
- Configuração guiada de VPN privada para acesso fora de casa e gestão de dispositivos integrada à interface.
- Gráficos históricos completos, métricas por processo de CPU e métricas específicas de jogos.
- Janela Workbench integrada com chat de IA local/online por configuração de ambiente; a interface não executa respostas da IA.\n- O chat exige Ollama local em execução ou variáveis de ambiente configuradas para provedor compatível; ainda falta cofre de credenciais do Windows e assistente de configuração.
- Roblox Studio Lab integrado para inspeção somente leitura de scripts .lua/.luau; mostra achados heurísticos e não executa nem aplica patches. A prévia de diff existe como função de biblioteca, mas a aplicação controlada ainda falta.
- Sandbox real para plugins externos.
- Workbench com criação e restauração confirmada de backup versionado, validação SHA-256 e cadastro de manifesto de plugin sem executar código. Ainda falta histórico visual completo, restauração de projeto inteiro e sandbox real.
- Empacotamento portátil completo com runtime incluído.

Consulte [ROADMAP.md](ROADMAP.md) para as etapas e limitações. Não considere recursos planejados como funcionalidades prontas.

## Como executar a versão atual
1. Instale Python 3 para Windows, se necessário: https://www.python.org/downloads/windows/
2. Durante a instalação, marque **Add python.exe to PATH**.
3. Baixe o ZIP da branch ou use **Code → Download ZIP**.
4. Extraia a pasta e execute `INICIAR_BLACKCORE.bat`.

O launcher precisa de uma instalação de Python existente; esta versão ainda não inclui o runtime Python dentro de uma pasta portátil.

## Testes
O workflow `.github/workflows/tests.yml` compila os módulos e executa testes unitários em Windows e Linux. O status real deve ser conferido na aba **Actions** depois que o workflow rodar.

## Segurança
- Não coloque tokens, senhas ou chaves de API no código público.
- Nenhum serviço de controle remoto deve ser exposto à internet sem autenticação, transporte seguro, expiração de sessão e revisão de segurança.
- Ações que alterem arquivos ou configurações devem apresentar o alvo e pedir aprovação.
- Não use a função de digitação em campos de senha, pagamentos ou comandos sensíveis.


## Configuração de IA e Workbench\n\nA interface agora inclui a janela **AI / Roblox Workbench**. No chat, a IA é chamada em segundo plano para não congelar a janela. Por padrão, usa Ollama em `http://127.0.0.1:11434/api/chat` com o modelo `llama3.2`. Instale e inicie o Ollama e baixe o modelo separadamente, ou configure um provedor compatível por variáveis de ambiente.\n\nPara API hospedada, configure `BLACKCORE_AI_PROVIDER=openai_compatible`, `BLACKCORE_AI_ENDPOINT` com URL HTTPS, `BLACKCORE_AI_API_KEY` no ambiente local e opcionalmente `BLACKCORE_AI_MODEL`. Não grave a chave em arquivos do projeto. A interface não oferece ainda um cofre de credenciais do Windows.\n\n### Workbench: Roblox, plugins e backups\n- Roblox Lab: escolha uma pasta para inspecionar scripts; o relatório é heurístico e somente leitura.\n- Plugins: cadastre um manifesto JSON, com aprovação explícita e zero permissões concedidas por padrão; nenhum código de plugin é carregado ou executado.\n- Backups: crie um backup de arquivo e restaure para um destino escolhido após confirmação e verificação do hash. Guarde os metadados junto do backup e proteja ambos; o hash de metadados não é uma assinatura digital.\n\n## Initial AI provider configuration
The provider layer is a library prototype and is not yet integrated into the graphical chat UI.

- Local Ollama is the default, using http://127.0.0.1:11434/api/chat unless BLACKCORE_AI_ENDPOINT is set.
- For an OpenAI-compatible hosted API, set BLACKCORE_AI_PROVIDER=openai_compatible, BLACKCORE_AI_ENDPOINT to an HTTPS endpoint, BLACKCORE_AI_API_KEY in the environment, and optionally BLACKCORE_AI_MODEL.
- Never put API keys in repository files, screenshots, or logs. The AI module returns text only and does not execute model output.

## Roblox Studio Lab prototype
The Lab accepts a local project folder, reads .lua/.luau files only, reports heuristic findings, and can generate a diff preview. It does not execute project code or apply patches.

## Etapa 6 — plugins e recuperação (protótipo implementado)
- O registro de plugins exige aprovação explícita, concede apenas permissões solicitadas e mantém plugins desativados por padrão.
- A ativação altera somente o estado do registro: plugins externos não são carregados nem executados.
- Backups versionados registram SHA-256; restauração exige confirmação e valida o hash antes de substituir o destino atomicamente.
- Ainda falta isolamento de processo/sandbox real, UI de gestão e testes em arquivos e ambientes reais do usuário.

## Etapa 7 — sessões remotas (primitivas implementadas)
- Código de pareamento de uso único, permissões mínimas, limitação de tentativas, expiração de sessão, revogação e auditoria sem registrar tokens.
- O módulo é independente do transporte: não abre portas, não transmite tela e não controla dispositivos por conta própria.
- Para controle real será necessário um app Android, um transporte criptografado autenticado (preferencialmente VPN privada), integração com a UI, testes de ameaça e validação em dispositivos. Não exponha uma porta de controle diretamente à internet.
