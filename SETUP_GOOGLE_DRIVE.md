# Configuração do Google Drive

Este aplicativo agora sincroniza os arquivos `config.xlsx` e `lancamentos.xlsx` com o Google Drive.

## Para usar sem autenticação (download apenas):

Os arquivos serão baixados automaticamente de `https://drive.google.com/drive/folders/14K09D1XwWXBDfnDWO89NX8MWb48iSvGR`

Neste modo:
- ✅ Os arquivos são baixados automaticamente
- ❌ Salvamento automático no Drive não funcionará (salva apenas localmente)

## Para usar com autenticação (download + upload):

Para fazer upload automático dos dados quando você salva, siga estes passos:

### 1. Crie uma Conta de Serviço no Google Cloud:

1. Vá para [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto (ou use um existente)
3. Ative a **Google Drive API**:
   - Clique em "APIs e Serviços"
   - Clique em "Ativar APIs e Serviços"
   - Procure por "Google Drive API" e clique em "Ativar"

### 2. Crie uma chave de conta de serviço:

1. Vá para "Credenciais"
2. Clique em "Criar Credenciais" → "Conta de Serviço"
3. Complete o formulário (nome arbitrário)
4. Na página seguinte, clique em "Criar Chave"
5. Escolha formato JSON
6. O arquivo JSON será baixado automaticamente

### 3. Configure o arquivo:

1. Renomeie o arquivo JSON baixado para `service_account.json`
2. Coloque-o na pasta raiz do projeto (mesmo local que `app.py`)

### 4. Compartilhe a pasta com a conta de serviço:

1. Abra o arquivo `service_account.json` com um editor de texto
2. Procure pelo campo `"client_email"` (exemplo: `seu-projeto@seu-projeto-iam.gserviceaccount.com`)
3. Copie esse email
4. Vá para a pasta no Google Drive que contém seus arquivos Excel
5. Compartilhe a pasta com este email (permissão de Editor)

### 5. Pronto!

Agora, quando você salvar configurações ou lançamentos, eles serão automaticamente enviados para o Google Drive.

## Solução de problemas:

**Q: Os arquivos não estão sendo baixados**
- Verifique se o link do Drive está acessível
- Verifique se os nomes dos arquivos são exatamente: `config.xlsx` e `lancamentos.xlsx`

**Q: Upload não funciona, mas download sim**
- Verifique se o arquivo `service_account.json` está presente
- Verifique se a conta de serviço tem permissão para editar a pasta
- Verifique se a pasta compartilhada existe e tem os arquivos

**Q: Erro de permissão**
- Certifique-se de que o email da conta de serviço foi compartilhado com permissão de "Editor"
- Aguarde alguns minutos para a permissão ser propagada
