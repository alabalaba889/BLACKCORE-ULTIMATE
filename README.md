# BLACKCORE ULTIMATE

Aplicativo local para Windows e outros sistemas com Python/Tkinter. Este repositório mantém a aplicação modular existente e inclui uma edição independente de arquivo único: **BLACKCORE_ULTIMATE_ONEFILE.py**.

## Edição de arquivo único

O arquivo **BLACKCORE_ULTIMATE_ONEFILE.py** reúne numa aplicação só:
- Dashboard de leitura de CPU/RAM/disco/rede e processos, usando psutil quando disponível.
- Telemetria opcional de GPU NVIDIA via nvidia-smi, se o utilitário já estiver instalado.
- Chat de IA com Ollama local ou API compatível com OpenAI via HTTPS, em uma thread separada para não congelar a interface.
- Roblox Studio Lab para leitura heurística de scripts .lua e .luau; não executa nem altera scripts.
- Prévia de diff textual; não aplica patches.
- Backup e restauração de arquivos com SHA-256 e confirmação explícita.
- Validação de manifesto de plugin. Nenhum código de plugin é importado ou executado.
- Abertura de aplicativos numa pequena lista permitida, sempre com confirmação.
- Aba de status que separa funções disponíveis de sistemas futuros.
- Log local em pasta de dados do usuário.

### Executar

Requisitos: Python 3.10 ou mais recente e Tkinter. psutil é opcional.

    python BLACKCORE_ULTIMATE_ONEFILE.py

Executar os testes embutidos sem abrir a interface:

    python BLACKCORE_ULTIMATE_ONEFILE.py --self-test

Os testes automatizados de CI também exercitam as funções centrais:

    python -m unittest discover -s tests -v

### Configurar IA

Padrão local: Ollama em http://127.0.0.1:11434/api/chat, modelo llama3.2. Instale/inicie o Ollama e baixe o modelo separadamente.

Para API compatível com OpenAI, configure no ambiente local:
- BLACKCORE_AI_PROVIDER=openai_compatible
- BLACKCORE_AI_ENDPOINT=https://... (endpoint HTTPS do provedor)
- BLACKCORE_AI_API_KEY (segredo local; nunca no código ou GitHub)
- BLACKCORE_AI_MODEL (opcional)

O chat devolve texto e nunca executa o conteúdo gerado pela IA. A configuração por variáveis de ambiente ainda não tem um assistente gráfico nem cofre dedicado de credenciais do Windows.

## Sistemas na aplicação modular existente

O projeto modular continua disponível através de blackcore.py e blackcore_core/. Essa versão contém o Workbench integrado e os módulos separados de AI provider, Roblox Lab, backups, plugins, sessões remotas abstratas e monitoramento. A edição de arquivo único é uma alternativa independente e não substitui automaticamente os módulos.

## O que ainda é futuro — não anunciar como pronto

- App Android real, transmissão de tela e comandos remotos autenticados.
- Acesso de fora de casa via VPN/rede privada, TLS, pareamento de dispositivo, revogação e testes de ameaça.
- Sandbox de processos para plugins de terceiros.
- Aplicação de patches no Roblox com backup, aprovação e testes posteriores.
- Memória persistente/projetos/anexos para a IA.
- Automação ampla de Windows com catálogo de ações, cancelamento global e permissões por ação.
- Atualização segura, assinatura, instalador com runtime embutido, desinstalação limpa e rollback.
- Testes de instalação limpa e validação em PC/Roblox Studio/Android reais.

O arquivo único não inicia servidor remoto nem abre portas de rede. O controle remoto só deve ser adicionado após existir um protocolo autenticado e criptografado, consentimento visível e revisão de segurança. Nunca exponha uma porta de controle diretamente à internet.

## Testes e publicação

GitHub Actions compila o código e executa testes unitários em Windows e Linux. Confira a aba Actions para o resultado do commit mais recente. Passar no CI não substitui testes no computador do usuário.

As alterações foram feitas na branch feature/ultimate-foundation; elas não passam automaticamente para main. Revisão e integração devem ocorrer depois de verificar os testes e o estado do PR.

## Segurança

- Nunca comite tokens, senhas ou chaves de API.
- Backups e metadados devem ser guardados juntos e protegidos; SHA-256 detecta divergência, mas não é assinatura digital.
- Roblox Lab é somente leitura; os achados são heurísticos, não uma prova de ausência de bugs.
- Plugins são apenas validados/cadastrados como metadados; nenhum plugin externo é executado.
- Ações locais pedem confirmação. Nenhuma saída de IA é interpretada como comando.
