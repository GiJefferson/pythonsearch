# pythonsearch
🔍 Python Ctrl+C Search &amp; Paste Tool v2.1.6 (Ferramenta inteligente de busca e colagem que encontra texto copiado (Ctrl+C) em arquivos e permite colar conteúdo modificado nas coordenadas exatas.)

# 🔍 Python Ctrl+C Search & Paste Tool v2.1.6

**Ferramenta inteligente de busca e colagem que encontra texto copiado (Ctrl+C) em arquivos e permite colar conteúdo modificado nas coordenadas exatas.**

## ✨ Principais Funcionalidades

### 🎯 Busca Inteligente com 6 Algoritmos
- **TIPO 1**: Comparação 100% literal (máxima precisão)
- **TIPO 2**: Arquivo completo igual ao texto copiado
- **TIPO 3**: Normalização de quebras de linha (`\r\n` ↔ `\n`)
- **TIPO 4**: Busca com `.strip()` aplicado nas pontas
- **TIPO 5**: Busca por probabilidade com âncoras inteligentes
- **TIPO 6**: Ignora completamente carriage returns (`\r`)

### 📋 Sistema Paste Automático
- Salva coordenadas exatas em XML
- Backup automático antes de modificações
- Ajuste automático de coordenadas no momento da colagem
- Correção para diferentes tipos de quebras de linha

### 🔧 Correções Avançadas (v2.1.6)
- **Quebras de linha diferentes**: Resolve incompatibilidades entre `\r\n` (Windows) e `\n` (Unix)
- **BOM UTF-8**: Detecta e ajusta automaticamente arquivos com Byte Order Mark
- **Mapeamento preciso**: Converte posições normalizadas para coordenadas originais
- **Encoding automático**: Detecta e trata diferentes encodings de arquivo

## 🚀 Como Usar

### 1. Buscar Texto
```bash
# Copie o texto desejado (Ctrl+C) e execute:
python pythonsearch.py
```
- O script encontra o texto em todos os arquivos da pasta configurada
- Salva as coordenadas no arquivo `sessionlinner.xml`
- Ordena resultados por confiabilidade

### 2. Colar Texto Modificado
```bash
# Modifique o texto, copie (Ctrl+C) e execute:
python pythonsearch.py paste

# Ou cole em arquivo específico:
python pythonsearch.py paste arquivo.js
```
- Cria backup automático antes da modificação
- Cola o novo texto nas coordenadas exatas do texto anterior
- Ajusta automaticamente para diferenças de formatação

### 3. Diagnóstico
```bash
# Para analisar problemas de coordenadas:
python pythonsearch.py diagnostico
```

## ⚙️ Configuração

Edite as variáveis no início do script:

```python
PASTA_BASE = r"C:\Users\USER\Desktop"  # Pasta para busca
EXTENSOES_NEGADAS = {".bak", ".bat"}                   # Extensões ignoradas
LIMITE_SIMILARIDADE_TIPO5 = 10.0                      # Similaridade mínima (%)
```

## 🎯 Casos de Uso Ideais

### 👨‍💻 Desenvolvimento de Software
- **Refatoração de código**: Encontre e substitua blocos específicos em múltiplos arquivos
- **Sincronização**: Mantenha trechos idênticos sincronizados entre arquivos
- **Templates**: Atualize templates em vários locais simultaneamente

### 📝 Edição de Documentos
- **Documentação técnica**: Atualize seções específicas em vários documentos
- **Configurações**: Modifique configurações em múltiplos arquivos
- **Versionamento manual**: Controle precisão em mudanças específicas

## 🔬 Sistema de Pontuação

Cada resultado recebe um score baseado no tipo de busca:

| Tipo | Score Base | Descrição |
|------|------------|-----------|
| TIPO 1 | 500 | 100% literal - máxima confiabilidade |
| TIPO 2 | 400 | Arquivo completo igual |
| TIPO 6 | 350 | Ignorando U+000D |
| TIPO 3 | 300 | Normalização de quebras (mais usado) |
| TIPO 4 | 200 | Com strip nas pontas |
| TIPO 5 | 100+ | Base + similaridade% |

## 📊 Exemplo de Workflow

1. **Encontrar código**:
   ```javascript
   // Copie este bloco e execute o script
   function processData(data) {
       return data.map(item => item.value);
   }
   ```

2. **Script encontra em múltiplos arquivos**:
   ```
   ✅ utils.js (TIPO1, score: 500.0)
   ✅ helper.js (TIPO3, score: 300.0) 
   ✅ main.js (TIPO5, score: 187.5, sim: 87.5%)
   ```

3. **Modificar e colar**:
   ```javascript
   // Modifique, copie e execute paste
   function processData(data) {
       return data.filter(item => item.active)
                  .map(item => item.value);
   }
   ```

4. **Resultado**: Todos os arquivos atualizados nas coordenadas exatas!

## 🛡️ Recursos de Segurança

- **Backup automático**: Cria backup com timestamp antes de qualquer modificação
- **Validação de coordenadas**: Verifica se o texto ainda está na posição esperada
- **Correção automática**: Ajusta coordenadas se detectar mudanças
- **Verificação de integridade**: Confirma que a colagem foi bem-sucedida

## 🔧 Requisitos

- Python 3.7+
- `pyperclip` para acesso à área de transferência

```bash
pip install pyperclip
```

## 📝 Saída XML

O script gera um arquivo `sessionlinner.xml` com:
- Coordenadas exatas de cada match
- Score de confiabilidade
- Informações de encoding e BOM
- Contexto do texto encontrado
- Metadados da busca

## 🚨 Problemas Resolvidos na v2.1.6

### ✅ Quebras de Linha Incompatíveis
**Problema**: Texto copiado do Windows (`\r\n`) não encontrado em arquivo Unix (`\n`)
**Solução**: Normalização inteligente e mapeamento preciso de coordenadas

### ✅ BOM UTF-8
**Problema**: Arquivos com BOM causavam offset nas coordenadas
**Solução**: Detecção automática e ajuste de coordenadas

### ✅ Coordenadas Incorretas no Paste
**Problema**: Paste em posição errada por diferenças de formatação
**Solução**: Recálculo automático de coordenadas no momento da colagem

---

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor:
1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo `LICENSE` para detalhes.

---

**💡 Dica**: Execute `python pythonsearch.py diagnostico` se encontrar problemas com coordenadas incorretas!
