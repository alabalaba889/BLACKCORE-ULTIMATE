# BLACKCORE ULTIMATE — foundation v0.2

Projeto portátil para Windows, construído por etapas. O aplicativo original foi preservado; esta branch adiciona uma base modular para monitoramento, confirmação de ações, backups, validação de plugins e testes automatizados.

## Já existe no repositório
- Interface Tkinter escura estilo terminal hacker.
- Monitoramento básico de CPU e RAM na interface original.
- Atalhos para abrir Bloco de Notas e Calculadora.
- Digitação de texto no aplicativo ativo após confirmação e contagem de 3 segundos.
- Simulações visuais reversíveis e log local.
- Módulo de métricas de disco e contadores de rede opcionais.
- Camada de autorização explícita para ações sensíveis.
- Helpers de backup e restauração que exigem confirmação explícita ao restaurar.
- Validador de manifesto de plugins (valida metadados e permissões; não executa plugins).
- Testes unitários e workflow de CI para Windows e Linux.

## Ainda não implementado
- Controle remoto real de mouse/teclado.
- Pareamento e controle Android pela rede local ou pela internet.
- Canal remoto seguro e gestão de sessões/dispositivos.
- Métricas reais de GPU e gráficos históricos integrados na interface.
- Integração com IA local/online e gestão de credenciais.
- Roblox Studio Lab funcional para inspecionar, testar e aplicar patches.
- Sandbox real para plugins externos.
- Reparação automática integrada e histórico de restauração na interface.
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
