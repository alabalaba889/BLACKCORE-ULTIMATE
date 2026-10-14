# BLACKCORE ULTIMATE — Android na mesma rede Wi-Fi

Este guia configura a base já existente: painel web/PWA, app Android e bridge Python no Windows. **A conexão de telemetria é somente leitura. Controle de tela, mouse e teclado não está implementado neste momento.**

## 1. Preparar o certificado local

O bridge exige HTTPS quando aceita conexões da rede. Não use HTTP na LAN nem desative a validação de certificados.

1. Instale o [mkcert](https://github.com/FiloSottile/mkcert) a partir da fonte oficial.
2. No PowerShell, dentro do projeto, descubra o IPv4 do PC com `ipconfig` (por exemplo, `192.168.1.20`). Use o endereço real do seu PC.
3. Execute `mkcert -install` no PC e crie o certificado para o IP real:

```powershell
New-Item -ItemType Directory -Force .\certs | Out-Null
mkcert -cert-file .\certs\blackcore-lan.pem -key-file .\certs\blackcore-lan-key.pem 192.168.1.20 localhost 127.0.0.1
mkcert -CAROOT
```

Troque `192.168.1.20` pelo IP mostrado no seu PC. O último comando mostra a pasta que contém `rootCA.pem`. **Nunca copie ou compartilhe `rootCA-key.pem`**: ele é a chave privada da autoridade certificadora.

## 2. Confiar na CA no Android

Para que o app e o Chrome validem o certificado da LAN, transfira apenas `rootCA.pem` para o telefone por um método privado. Nas configurações Android, procure a opção para instalar um certificado de CA (o nome exato varia por fabricante) e selecione esse arquivo. Confirme apenas se você acabou de criar a CA no seu PC e confia nela. A instalação de uma CA de usuário amplia o que o aparelho confia; remova-a quando não precisar mais.

Não ignore avisos de certificado e não instale certificados recebidos de terceiros. O app Android usa a configuração de segurança da rede para aceitar CAs instaladas pelo usuário, além das CAs do sistema.

## 3. Iniciar o bridge no Windows

No PowerShell, a partir da raiz do repositório:

```powershell
$env:BLACKCORE_BRIDGE_TOKEN = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
python -m blackcore_core.mobile_bridge --host 0.0.0.0 --port 8765 --cert .\certs\blackcore-lan.pem --key .\certs\blackcore-lan-key.pem
```

Mantenha essa janela aberta. O token vale para esse processo; não o publique, não o envie em capturas de tela e não o coloque no Git. A porta só deve ser permitida no perfil **Private** do Firewall do Windows e, de preferência, limitada ao endereço/IP do seu telefone ou à sub-rede doméstica. Não crie encaminhamento de porta no roteador.

## 4. Conectar o Android

- Confirme que PC e telefone estão na mesma rede Wi-Fi (sem rede de convidados/isolamento de clientes).
- No painel do Chrome, abra `https://IP-DO-PC:8765/`; no app, informe `https://IP-DO-PC:8765`.
- Cole o token gerado no PowerShell e toque em **Conectar**.
- Se não conectar, confira o IP atual do PC, o certificado, o token e o Firewall. Não desative a validação TLS para “fazer funcionar”.
- O painel web pode ser adicionado à tela inicial pelo menu do Chrome, se o navegador oferecer essa opção.

## 5. Limites atuais e validação

O bridge oferece `GET /api/health` e telemetria autenticada em `GET /api/status`. Ele recusa métodos que alteram dados. Esta configuração **não** adiciona controle remoto: streaming de tela, mouse/teclado e execução de comandos continuam desativados e não devem ser tratados como implementados.

Antes de considerar pronto, verifique a execução da workflow **BLACKCORE mobile checks** no GitHub Actions, instale o APK de debug gerado por uma execução bem-sucedida e teste a conexão num PC e num Android reais. O APK de debug não é um pacote de distribuição pública assinado.
