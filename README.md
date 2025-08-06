# AI Helm Values Generator

Um GitHub Action que utiliza Inteligência Artificial para gerar valores otimizados do Helm com base em análise de contexto operacional.

## 🎯 Funcionalidades

- Analisa incidentes operacionais e métricas para identificar problemas
- Gera recomendações inteligentes para valores do Helm
- Suporta múltiplos provedores de IA (GitHub Models, OpenAI)
- Aplica automaticamente as recomendações aos valores atuais
- Fornece justificativas detalhadas para cada mudança

## 📋 Inputs

| Input | Descrição | Obrigatório | Padrão |
|-------|-----------|-------------|---------|
| `app_name` | Nome da aplicação | ✅ | - |
| `environment` | Ambiente de deploy (dev/staging/prod) | ✅ | - |
| `current_values` | Conteúdo atual do values.yaml (codificado em base64) | ✅ | - |
| `operational_context` | Contexto operacional em YAML (codificado em base64) | ✅ | - |
| `helm_templates` | Conteúdo dos templates Helm (array JSON) | ❌ | `[]` |
| `ai_provider` | Provedor de IA (github/openai) | ❌ | `copilot` |
| `ai_token` | Token da API do provedor de IA | ❌ | - |
| `ai_model` | Modelo de IA a utilizar | ❌ | `gpt-4o` |

## 📤 Outputs

| Output | Descrição |
|--------|-----------|
| `generated_values` | Conteúdo do values.yaml gerado |
| `ai_analysis` | Análise e recomendações da IA |
| `changes_summary` | Resumo das mudanças realizadas |

## 🚀 Como Usar

### Exemplo Básico

```yaml
- name: Gerar valores otimizados com IA
  uses: ./
  with:
    app_name: "minha-app"
    environment: "production"
    current_values: ${{ env.CURRENT_VALUES_B64 }}
    operational_context: ${{ env.OPERATIONAL_CONTEXT_B64 }}
    ai_provider: "copilot"
    ai_token: ${{ secrets.GITHUB_TOKEN }}
```

### Exemplo Completo

```yaml
name: Otimização Inteligente do Helm
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Ambiente'
        required: true
        default: 'staging'
        type: choice
        options:
          - dev
          - staging
          - prod

jobs:
  optimize-helm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Preparar contexto operacional
        run: |
          # Coletar métricas e incidentes recentes
          cat > operational-context.yaml << EOF
          recent_incidents:
            - type: "high_memory_usage"
              description: "Aplicação atingiu 95% do limite de memória"
              timestamp: "2024-01-15T10:30:00Z"
              severity: "high"
          
          metrics:
            avg_cpu_usage: 0.75
            avg_memory_usage: 0.85
            p99_response_time: 2500ms
            error_rate: 0.05
          
          resource_constraints:
            current_replicas: 3
            max_cpu_per_pod: "1"
            max_memory_per_pod: "2Gi"
          EOF
          
          # Codificar em base64
          echo "OPERATIONAL_CONTEXT_B64=$(cat operational-context.yaml | base64 -w 0)" >> $GITHUB_ENV
          echo "CURRENT_VALUES_B64=$(cat helm/values.yaml | base64 -w 0)" >> $GITHUB_ENV
      
      - name: Gerar valores otimizados
        id: optimize
        uses: ./
        with:
          app_name: "minha-aplicacao"
          environment: ${{ inputs.environment }}
          current_values: ${{ env.CURRENT_VALUES_B64 }}
          operational_context: ${{ env.OPERATIONAL_CONTEXT_B64 }}
          ai_provider: "copilot"
          ai_token: ${{ secrets.GITHUB_TOKEN }}
          ai_model: "gpt-4o"
      
      - name: Salvar valores otimizados
        run: |
          echo "${{ steps.optimize.outputs.generated_values }}" > helm/values-optimized.yaml
          
      - name: Mostrar análise da IA
        run: |
          echo "## 🤖 Análise da IA"
          echo "${{ steps.optimize.outputs.ai_analysis }}"
          echo ""
          echo "## 📊 Resumo das Mudanças"
          echo "${{ steps.optimize.outputs.changes_summary }}"
```

## 📊 Formato do Contexto Operacional

O contexto operacional deve ser fornecido em formato YAML com a seguinte estrutura:

```yaml
recent_incidents:
  - type: "out_of_memory"
    description: "Pod foi reiniciado por falta de memória"
    timestamp: "2024-01-15T10:30:00Z"
    severity: "critical"
  - type: "slow_response"
    description: "Tempo de resposta acima de 5s"
    timestamp: "2024-01-15T11:00:00Z"
    severity: "medium"

metrics:
  avg_cpu_usage: 0.85        # 85% em média
  avg_memory_usage: 0.90     # 90% em média
  p99_response_time: 3000ms  # 3 segundos no p99
  error_rate: 0.02           # 2% de taxa de erro
  requests_per_second: 1500

resource_constraints:
  current_replicas: 2
  max_cpu_per_pod: "500m"
  max_memory_per_pod: "1Gi"
  node_capacity: "4 cores, 8Gi RAM"

alerts:
  - name: "HighMemoryUsage"
    status: "firing"
    duration: "5m"
```

## 🔧 Configuração dos Provedores de IA

### GitHub Models (Copilot)
```yaml
ai_provider: "copilot"
ai_token: ${{ secrets.GITHUB_TOKEN }}
ai_model: "gpt-4o"  # ou gpt-4, gpt-3.5-turbo
```

### OpenAI
```yaml
ai_provider: "openai"
ai_token: ${{ secrets.OPENAI_API_KEY }}
ai_model: "gpt-4"  # ou gpt-3.5-turbo
```

## 🎯 Tipos de Otimizações

A IA pode sugerir otimizações para:

- **Recursos**: CPU e memória (requests/limits)
- **Autoscaling**: Min/max replicas e métricas de escala
- **Health Checks**: Configurações de liveness/readiness probes
- **Configurações de Pod**: Tolerations, node affinity
- **Networking**: Service e ingress settings

## ⚠️ Requisitos

- GitHub Actions runner
- Token de API válido para o provedor de IA escolhido
- Inputs codificados em base64 (para evitar problemas com caracteres especiais)

## 🤝 Contribuindo

1. Fork este repositório
2. Crie uma branch para sua feature
3. Faça commit das mudanças
4. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.
