# BLACKCORE ULTIMATE — plano de conclusão por etapas

Este plano é a referência de execução para completar a versão Android + Windows. O código existente deve ser reutilizado; nenhum item será chamado de concluído apenas porque há um botão ou uma tela.

## Ordem de implementação

| Etapa | Entrega | Como será adicionada | Critério para marcar concluída |
|---|---|---|---|
| 0. Verificação da base | CI, build Android, testes Python/JS | Rodar a workflow, corrigir falhas de compilação e testes antes de empilhar recursos | Workflow verde e APK de debug produzido |
| 1. Transporte seguro | HTTPS local, token, firewall, configuração de CA | TLS 1.2+, token em memória, documentação de CA privada, nenhuma porta exposta à internet | Testes de autenticação/TLS e teste real na LAN |
| 2. Painel e APK | Métricas, atualização, desconexão, mensagens de erro | Reutilizar PWA e Compose; estados claros de conexão e atualização | JS/Kotlin compilam e telas testadas em Android |
| 3. Controle remoto opcional | Captura estática, mouse, clique, texto e teclas permitidas | Bridge Windows opt-in, endpoint autenticado, confirmação explícita, allowlist, validação de coordenadas, limite de texto e rate limit | Testes negativos/positivos em PC de teste; recurso desligado por padrão |
| 4. Sessões e auditoria | Pareamento, revogação, logs de ações | IDs de sessão, expiração, revogação, log sem token/senhas e opção de encerrar tudo | Testes de expiração, revogação e ausência de segredos nos logs |
| 5. Automação de aplicativos | Abrir aplicativos permitidos e sequências locais | Lista permitida por configuração; cada ação exige autorização e tem botão de parar | Testes com apps de demonstração, sem executar comandos arbitrários |
| 6. Monitor de desempenho | CPU, RAM, disco, rede, processos e métricas de jogo disponíveis | Amostrar métricas suportadas; indicar N/D quando o hardware/driver não fornece o dado | Testes de coleta e atualização; nenhuma métrica inventada |
| 7. Roblox Studio Lab | Diagnóstico e prévia de alterações | Começar em leitura/preview de diff; aplicar mudanças apenas com confirmação e backup | Testes em projeto de exemplo e rollback verificado |
| 8. Plugins | Manifestos, permissões e catálogo | Validar manifestos, permissões explícitas e sandbox; não executar plugins não confiáveis no processo principal | Testes de permissão, isolamento e rejeição de plugin inválido |
| 9. Backup e self-repair | Diagnóstico, backup, restauração e rollback | Snapshot com hash, cópia para destino separado, confirmação antes de restaurar e log | Teste de corrupção, restauração e verificação de hash |
| 10. Test Lab | Logs, testes unitários, integração, E2E e health checks | Ampliar a CI e incluir cenários de conexão, token inválido, perda de rede e build APK | Relatório de testes reproduzível e falhas bloqueiam release |
| 11. Acesso remoto fora de casa | VPN privada e instruções de conexão | Recomendar VPN existente (por exemplo, Tailscale/WireGuard) em vez de expor porta; configuração manual e verificável | Conexão remota testada por VPN, sem port-forwarding público |
| 12. Distribuição | Instalador Windows, APK assinado e atualizações | Separar debug de release; assinatura controlada pelo dono, versionamento e rollback | Pacotes assinados, checksums e teste de instalação/atualização |

## Estado atual deste trabalho

- **Adicionado ao código, ainda não validado em execução:** bridge com controle remoto opt-in; captura de tela estática; ações limitadas de mouse, clique, texto e teclas allowlisted; UI web e UI Android com consentimento explícito; atualização automática de telemetria no Android.
- **Adicionado:** testes para confirmar que o controle remoto permanece desligado por padrão e exige TLS para ativação.
- **Adicionado:** dependência opcional em `requirements-remote-control.txt` e instruções de configuração local.
- **Ainda precisa de verificação:** workflow CI, compilação Kotlin/Gradle, execução dos testes Python/JS e teste físico no Android/Windows.
- **Ainda não implementado:** sessões com expiração/revogação, automação de aplicativos completa, sandbox de plugins, VPN integrada, self-repair completo, instalador Windows e distribuição Android assinada.
- **Limite importante:** a captura de tela atual é uma imagem estática sob demanda, não streaming contínuo. O bridge não aceita shell/comandos arbitrários.

## Regras de segurança

1. O controle remoto fica desligado por padrão; só o processo iniciado com `--enable-remote-control` o ativa.
2. O bridge de rede exige TLS. Nunca desative a validação de certificado para contornar erros.
3. Nunca faça port-forwarding público do bridge; para fora de casa, use VPN privada.
4. Tokens, chaves privadas e credenciais não entram no Git, logs, PWA cache ou APK.
5. Toda ação remota precisa de token válido, consentimento da interface e validação no servidor.
6. Não marcar uma etapa como pronta sem testes automatizados e, quando envolver hardware/rede, teste real documentado.
