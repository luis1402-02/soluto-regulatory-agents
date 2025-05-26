import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Métricas customizadas
const errorRate = new Rate('errors');

// Configuração do teste
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up para 10 usuários
    { duration: '1m', target: 10 },    // Manter 10 usuários por 1 minuto
    { duration: '30s', target: 20 },   // Ramp up para 20 usuários
    { duration: '1m', target: 20 },    // Manter 20 usuários por 1 minuto
    { duration: '30s', target: 0 },    // Ramp down para 0
  ],
  thresholds: {
    'http_req_duration': ['p(95)<5000'], // 95% das requisições < 5s
    'errors': ['rate<0.1'],              // Taxa de erro < 10%
  },
};

// Queries de teste
const testQueries = [
  {
    query: "Quais são os requisitos do Banco Central para fintechs?",
    context: "Análise para fintech de pagamentos",
    priority: "high"
  },
  {
    query: "Regulamentações ANVISA para dispositivos médicos classe II",
    context: "Desenvolvimento de monitor cardíaco",
    priority: "critical"
  },
  {
    query: "Compliance LGPD para processamento de dados sensíveis",
    context: "Sistema de saúde digital",
    priority: "medium"
  },
  {
    query: "Normas CVM para ofertas públicas de tokens",
    context: "Plataforma de tokenização",
    priority: "high"
  },
  {
    query: "Requisitos ANATEL para IoT devices",
    context: "Dispositivos de telemetria",
    priority: "medium"
  }
];

export default function () {
  // Seleciona uma query aleatória
  const query = testQueries[Math.floor(Math.random() * testQueries.length)];
  
  // Faz a requisição
  const res = http.post(
    'http://localhost:2024/api/analyze',
    JSON.stringify(query),
    {
      headers: { 
        'Content-Type': 'application/json',
      },
      timeout: '30s',
    }
  );

  // Verifica o resultado
  const success = check(res, {
    'status é 200': (r) => r.status === 200,
    'resposta tem output': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.output !== null && body.output !== undefined;
      } catch (e) {
        return false;
      }
    },
    'resposta em menos de 5s': (r) => r.timings.duration < 5000,
  });

  errorRate.add(!success);

  // Pausa entre requisições
  sleep(Math.random() * 3 + 2); // Entre 2-5 segundos
}

// Função executada uma vez no final
export function handleSummary(data) {
  console.log('=== Resumo do Teste de Carga ===');
  console.log(`Duração Total: ${data.metrics.iteration_duration.values.avg}ms`);
  console.log(`Taxa de Erro: ${data.metrics.errors.values.rate * 100}%`);
  console.log(`Requisições/s: ${data.metrics.http_reqs.values.rate}`);
  
  return {
    'stdout': JSON.stringify(data, null, 2),
    'load-test-results.json': JSON.stringify(data, null, 2),
  };
}