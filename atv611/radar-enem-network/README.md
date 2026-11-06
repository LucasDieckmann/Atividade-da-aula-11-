# Mini Radar ENEM — Redes e Containers com Docker

## Estrutura do laboratório

A arquitetura segue a segmentação:

- `frontend-net`: 172.20.10.0/24 — rede pública/DMZ
- `backend-net`: 172.20.20.0/24 — rede interna isolada (`internal: true`)

Serviços:

- `radar-proxy` — ingress público em `:8080` e reverse proxy para o backend
- `radar-backend` — conectividade em dupla interface, público e privada
- `radar-db` — PostgreSQL em rede interna, sem exposição host

## Arquivo principal

- `docker-compose.yml`
- `nginx.conf`

## Subir o ambiente

```bash
cd radar-enem-network
docker compose up -d
```

## Validar o acesso público

```bash
curl -i http://localhost:8080
```

## Diagnóstico e desafios

### 1) DNS interno do Docker

```bash
docker exec -it radar-proxy cat /etc/resolv.conf
docker exec -it radar-proxy nslookup radar-backend
docker exec -it radar-proxy nslookup radar-db
```

Resultado esperado:

- `radar-backend` resolve dentro da rede por nome
- `radar-db` não resolve desde a `frontend-net` porque não participa da rede pública
- o servidor DNS interno do Docker responde apenas dentro da rede conectada

### 2) Multi-homing e rota padrão

```bash
docker exec -it radar-backend ip addr show
docker exec -it radar-backend ip route show
```

A interface com a rota padrão é a da rede pública (`frontend-net`) porque o backend precisa receber o tráfego do reverse proxy e manter as conexões externas; a rede privada é usada apenas para o banco.

### 3) Queda de rota e erro 502

```bash
docker network disconnect radar-enem-network_frontend-net radar-backend
curl -i http://localhost:8080

docker network connect --ip 172.20.10.20 radar-enem-network_frontend-net radar-backend
```

Quando a interface pública do backend é removida, o Nginx não consegue alcançar o upstream e responde `502 Bad Gateway`.

### 4) Acesso administrativo seguro via bastion host

```bash
docker run --rm -it --network radar-enem-network_backend-net \
  postgres:15-alpine psql -h 172.20.20.50 -U radar_admin -d radarenem -c "\l"
```

Senha: `enem_secret_2026`

## Observações de segurança

- o banco não expõe portas para o host
- o proxy é o único ponto de entrada
- a rede `backend-net` é `internal`, impedindo acesso externo direto
- o backend atua como ponte multi-homed entre as redes

## Relatório técnico

### Isolamento em camadas

O `radar-proxy` não consegue pingar nem resolver o nome do `radar-db` porque o PostgreSQL está em uma rede interna isolada, sem conexão com a `frontend-net`. Também não há resolução pública para nomes de serviços privados; o DNS interno do Docker só responde para containers conectados à mesma rede ou redes conectadas à mesma composição. A rede `backend-net` foi configurada com `internal: true`, então ela não recebe roteamento para fora do Docker host e não expõe a porta do banco.

Isso impede que um atacante que comprometa o Nginx público explore diretamente o PostgreSQL, pois o banco fica fora da rede de entrada e a infraestrutura exige que a conexão passe pelo backend, que já está na camada de aplicação e em outra sub-rede.

### Princípio da exposição mínima e NAT

Colocar o PostgreSQL em uma sub-rede pública, mesmo com senha forte, viola o princípio da exposição mínima, porque o banco deixa de ser um serviço privado e passa a ter superfície de ataque aberta à internet. O objetivo do design é expor apenas o fluxo necessário para o usuário externo e manter o banco em uma rede privada sem rota pública.

No contexto da nuvem, o NAT Gateway permite que a sub-rede privada (backend) envie tráfego de saída para a internet sem receber conexões inbound diretas. Assim, o backend pode baixar atualizações, arquivos do INEP ou pacotes de software sem expor um endereço público do banco ou dos serviços internos.
