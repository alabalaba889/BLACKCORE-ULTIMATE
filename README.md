# BLACKCORE ULTIMATE

Aplicativo local para Windows com uma edição Python independente e uma nova base mobile em desenvolvimento. As funcionalidades abaixo são separadas por estágio; não confunda o painel mobile com controle remoto completo.

## Edição Windows de arquivo único

**BLACKCORE_ULTIMATE_ONEFILE.py** inclui:
- Monitoramento de CPU/RAM/disco/rede/processos e telemetria opcional NVIDIA.
- Chat de IA com Ollama local ou API compatível com OpenAI via HTTPS.
- Roblox Studio Lab em modo somente leitura e prévia de diff.
- Backup/restauração com SHA-256 e confirmação.
- Validação de manifesto de plugins sem executar código externo.
- Abertura confirmada de alguns aplicativos permitidos e logs locais.

Requisitos: Python 3.10+ e Tkinter. Execute `python BLACKCORE_ULTIMATE_ONEFILE.py`. Testes: `python -m unittest discover -s tests -v`.

## Mobile — implementação inicial

### Painel web instalável (PWA)
O diretório `mobile_web/` contém uma interface responsiva que pode ser instalada pelo navegador compatível. Ela conecta ao bridge e lê CPU, memória e disco. O cache offline cobre somente a interface; dados do PC exigem conexão.

### Aplicativo Android (projeto fonte)
O diretório `android/` contém um projeto Kotlin/Jetpack Compose com formulário de endereço HTTPS/token e consulta de telemetria. O cliente exige HTTPS e confia nos certificados aceitos pelo Android. O APK de debug só deve ser considerado gerado quando o job Android no GitHub Actions terminar com sucesso.

### Bridge de telemetria no PC
O módulo `blackcore_core/mobile_bridge.py` fornece endpoints de leitura autenticados por bearer token:
- `GET /api/health` — estado básico do serviço.
- `GET /api/status` — métricas autenticadas.
- Outros caminhos retornam 404; métodos POST/PUT/DELETE são recusados.

Por segurança, o padrão é bind apenas em `127.0.0.1`. Um bind de rede (por exemplo, `0.0.0.0`) exige certificado TLS, chave e token de pelo menos 32 caracteres. Gere o token fora do repositório e guarde-o como segredo local `BLACKCORE_BRIDGE_TOKEN`. Para uma rede local, o certificado precisa ter o endereço usado pelo celular no SAN e ser confiável no dispositivo; um certificado inválido não deve ser contornado. Instale `psutil` opcionalmente para CPU/RAM.

Exemplo de execução local no Windows PowerShell:
```powershell
$env:BLACKCORE_BRIDGE_TOKEN = "substitua-por-um-segredo-aleatorio-com-32-caracteres-ou-mais"
python -m blackcore_core.mobile_bridge
```

O modo padrão localhost serve para diagnóstico no próprio PC, não para conectar de outro aparelho. Para habilitar Wi-Fi local, configure TLS/certificado confiável e rode com `--host 0.0.0.0 --cert caminho\cert.pem --key caminho\key.pem`. Restrinja a porta no firewall. Para uso fora de casa, prefira uma VPN privada que torne o PC acessível apenas aos seus dispositivos; não encaminhe a porta do bridge diretamente para a internet. Nunca compartilhe o token.

## Ainda não implementado

- Controle de tela ao vivo, mouse/teclado remoto, automação de aplicativos ou execução remota de comandos.
- Pareamento de dispositivos com expiração/revogação, gestão de vários usuários e auditoria de sessões.
- Configuração automatizada de VPN e certificado, criação de APK assinado para distribuição e publicação na Play Store.
- Sandbox de plugins, aplicação automática de patches, memória persistente de IA, instalador Windows assinado e rollback.
- Validação manual em dispositivos Android e em PCs reais.

O bridge atual é **somente leitura**; o painel web e o app Android não podem controlar o PC. A autenticação por token não substitui TLS, certificado confiável, firewall e VPN para uso remoto.

## IA

Ollama local é a opção padrão do arquivo único. Para provedor compatível com OpenAI, configure `BLACKCORE_AI_PROVIDER=openai_compatible`, `BLACKCORE_AI_ENDPOINT=https://...`, `BLACKCORE_AI_API_KEY` e opcionalmente `BLACKCORE_AI_MODEL`. Nunca grave chaves no código ou no GitHub.

## Testes e GitHub

A workflow existente testa Python em Windows/Linux. A workflow mobile testa arquivos web e tenta montar o APK Android de debug. Confira os resultados em [GitHub Actions](https://github.com/alabalaba889/BLACKCORE-ULTIMATE/actions). CI verde não substitui testes no seu computador/celular.

Todo o trabalho está na branch `feature/ultimate-foundation`; isso não significa que foi mesclado em `main`.

## Segurança

- A IA não executa texto que ela própria gerar.
- Plugins são metadados e não são executados.
- Roblox Lab não altera scripts.
- SHA-256 detecta alterações nos backups, mas não é assinatura digital.
- Não use HTTP para telemetria fora do próprio computador e nunca exponha o bridge diretamente à internet.
