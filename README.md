# BLACKCORE ULTIMATE

BLACKCORE ULTIMATE combina uma aplicação local para Windows com uma base mobile Android e um painel web. Este README separa recursos implementados de capacidades futuras; uma tela não significa que o controle remoto correspondente exista.

## Edição Windows de arquivo único

**BLACKCORE_ULTIMATE_ONEFILE.py** inclui:
- Monitoramento de CPU/RAM/disco/rede/processos e telemetria opcional NVIDIA.
- Chat de IA com Ollama local ou API compatível com OpenAI.
- Roblox Studio Lab em modo somente leitura e prévia de diff.
- Backup/restauração com SHA-256 e confirmação.
- Validação de manifesto de plugins sem executar código externo.
- Abertura confirmada de alguns aplicativos permitidos e logs locais.

Requisitos: Python 3.10+ e Tkinter. Execute `python BLACKCORE_ULTIMATE_ONEFILE.py`. Testes: `python -m unittest discover -s tests -v`.

## Mobile: o que foi implementado

### Painel web/PWA
O diretório `mobile_web/` contém uma interface responsiva que pode ser instalada pelo navegador compatível. Inclui:
1. validação de URL e HTTPS;
2. validação mínima do token;
3. token não persistido em armazenamento web;
4. mostrar/ocultar token;
5. medição de latência;
6. timeout de requisição;
7. atualização manual;
8. atualização automática;
9. seleção do intervalo de atualização;
10. desconexão com limpeza do token;
11. copiar resumo;
12. exportar diagnóstico JSON;
13. CPU;
14. RAM usada/total;
15. RAM disponível;
16. disco usado/livre;
17. totais de rede enviada/recebida;
18. contadores de pacotes;
19. tempo ligado do sistema;
20. contagem de processos;
21. núcleos lógicos;
22. bateria quando o hardware fornece esse dado;
23. tempo ligado do bridge;
24. visualização de JSON bruto;
25. layout adaptável a celular/tablet/desktop;
26. mensagens de estado acessíveis;
27. cache offline apenas para os arquivos da interface, nunca para a API;
28. Content Security Policy sem scripts inline;
29. política de cache `no-store` para telemetria;
30. erros de conexão e autenticação mais claros.

As métricas opcionais aparecem como N/D quando o sistema ou a biblioteca `psutil` não as fornece.

### Aplicativo Android
Guia de configuração para Android na mesma rede Wi-Fi: [`ANDROID_WIFI_SETUP.md`](ANDROID_WIFI_SETUP.md). O guia cobre TLS local, instalação da CA no telefone, início do bridge e limites atuais.

O diretório `android/` contém o projeto fonte Kotlin/Jetpack Compose. O app conecta por HTTPS, envia um token bearer em memória e exibe telemetria em modo somente leitura. A CI compila um APK de debug e publica o arquivo como artefato apenas se o job concluir com sucesso. APK de debug não é um pacote assinado para distribuição pública.

### Bridge no PC
O módulo `blackcore_core/mobile_bridge.py` hospeda o painel e os endpoints na mesma origem:
- `GET /api/health` — estado básico sem dados sensíveis.
- `GET /api/status` e `GET /api/v1/status` — telemetria autenticada.
- Caminhos desconhecidos retornam 404; métodos que alterariam dados são recusados.
- Token mínimo de 32 caracteres, comparação de token em tempo constante e TLS 1.2+ obrigatório para bind fora do loopback.
- Rotas de arquivos são allowlist, respostas têm cabeçalhos de segurança e a API não é armazenada no cache da PWA.

### Iniciar no PC
É necessário que o bridge esteja executando no PC. No momento, ele usa Python; este repositório não consegue fazer o celular iniciar um processo arbitrário no Windows pela rede sem um serviço previamente ativo e autorizado.

No PowerShell do PC:
```powershell
$env:BLACKCORE_BRIDGE_TOKEN = "use-um-segredo-aleatorio-com-32-caracteres-ou-mais"
python -m blackcore_core.mobile_bridge
```

Esse exemplo usa o padrão `127.0.0.1`, acessível apenas no próprio PC. Para Wi-Fi, é necessário configurar um certificado TLS confiável para o endereço do PC, e executar com `--host 0.0.0.0 --cert caminho\cert.pem --key caminho\key.pem`. Restrinja a porta no firewall. Para acesso de fora de casa, prefira uma VPN privada; não encaminhe a porta do bridge diretamente para a internet. Não contorne avisos de certificado e nunca compartilhe o token.

**Importante:** “sem instalador” é possível; “sem nada executando no PC” não é. Android, navegadores e Windows impedem que uma página do celular instale ou inicie silenciosamente uma GUI no PC. Para a conexão ser possível, precisa haver um agente/servidor já autorizado no PC (ou um recurso remoto nativo previamente habilitado). Esta versão ainda não tem controle de tela, mouse/teclado, execução de comandos, leitura remota de arquivos ou automação de jogos.

## Revisão/refatoração do mobile
Foram revisados e melhorados 15 pontos estruturais, sem apagar aleatoriamente recursos já existentes:
1. CSS separado do HTML;
2. JavaScript separado do HTML;
3. remoção de JavaScript inline;
4. remoção de estilos inline;
5. CSP sem `unsafe-inline`;
6. allowlist explícita de arquivos estáticos;
7. bloqueio de traversal de caminhos;
8. timeout e cancelamento de requisição;
9. erros HTTP tratados por categoria;
10. credenciais não persistidas no navegador;
11. cache da API desabilitado;
12. ciclo de cache PWA versionado;
13. requisições mutáveis recusadas no bridge;
14. TLS exigido para bind de rede;
15. métricas opcionais degradam graciosamente quando não suportadas.

## Controle remoto opcional — em desenvolvimento

O bridge e as interfaces agora incluem uma primeira implementação **opt-in** para captura estática de tela e ações limitadas de mouse/clique/texto/teclas permitidas. O controle remoto permanece desligado por padrão. Para habilitar no Windows, instale a dependência opcional com `python -m pip install -r requirements-remote-control.txt` e inicie o bridge com `--enable-remote-control`, certificado TLS e chave privada. A tela é uma captura estática sob demanda, não vídeo contínuo. Esta implementação ainda requer validação por CI e testes reais antes de ser considerada pronta.

O app Android inclui controles com confirmação explícita, captura de tela sob demanda e atualização automática de telemetria. Esses recursos de interface não provam que o bridge remoto está habilitado ou que a compilação passa; confira a workflow antes de instalar.

Plano detalhado e ordem de trabalho: [ROADMAP_COMPLETION.md](ROADMAP_COMPLETION.md).

## Ainda não implementado
- Streaming contínuo de tela; controle remoto ainda precisa de validação de segurança, testes de integração e testes reais.
- Pareamento com expiração/revogação, múltiplos usuários e auditoria de sessões.
- Configuração automatizada e segura de certificados/VPN.
- Sandbox de plugins, aplicação automática de patches e memória persistente da IA.
- Instalador Windows assinado, atualização/rollback automáticos e publicação na Play Store.
- Testes manuais em dispositivos Android e PCs reais.

## IA
Ollama local é a opção padrão do arquivo único. Para um provedor compatível com OpenAI, configure `BLACKCORE_AI_PROVIDER=openai_compatible`, `BLACKCORE_AI_ENDPOINT=https://...`, `BLACKCORE_AI_API_KEY` e opcionalmente `BLACKCORE_AI_MODEL`. Nunca grave chaves no código ou no GitHub.

## CI, artefatos e branch
A workflow mobile valida Python, testes unitários, sintaxe JavaScript e tenta compilar o APK Android. Se a compilação terminar com sucesso, o APK de debug fica disponível nos artefatos da execução. Confira [GitHub Actions](https://github.com/alabalaba889/BLACKCORE-ULTIMATE/actions).

Todo o trabalho está em `feature/ultimate-foundation`; isso não significa que foi mesclado em `main`. CI verde não substitui testes no celular e no PC real.

## Segurança
- A IA não executa o próprio texto gerado.
- Plugins são metadados e não são executados.
- Roblox Lab não altera scripts.
- SHA-256 detecta alterações nos backups, mas não é assinatura digital.
- Não exponha o bridge diretamente à internet.
