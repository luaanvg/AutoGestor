# Guia de estudo prático do AutoGestor

O sistema já está montado, mas o objetivo não é apenas executá-lo. Estude uma
parte por vez, altere pequenos comportamentos e confirme o resultado na tela.

## Sessão 1 — entender a estrutura do Django

Leia nesta ordem:

1. `manage.py`;
2. `app/settings.py`;
3. `app/urls.py`;
4. `cars/apps.py`;
5. `cars/urls.py`.

Objetivo: entender como uma URL chega até uma view.

Exercício: altere temporariamente o título `AutoGestor` em `base.html`, atualize
o navegador e observe a mudança.

## Sessão 2 — banco de dados e relacionamentos

Leia `cars/models.py` até o fim.

Observe:

- `ForeignKey`: vários veículos podem pertencer a uma marca;
- `ManyToManyField`: uma marca pode fabricar vários tipos de veículo;
- `related_name`: permite fazer consultas no sentido inverso;
- `choices`: limita os valores possíveis de status;
- `UniqueConstraint`: impede duas vendas confirmadas para o mesmo veículo;
- `PROTECT`: impede apagar um registro necessário para uma venda.

Exercício: abra o shell com `py manage.py shell` e teste:

```python
from cars.models import Vehicle
Vehicle.objects.count()
Vehicle.objects.filter(status="available")
Vehicle.objects.select_related("brand", "vehicle_type").first()
```

## Sessão 3 — formulários e validação

Leia `cars/forms.py`.

Entenda a diferença:

- o form valida o que veio da tela;
- o model protege a regra mesmo se o dado vier do admin, shell ou futura API.

Exercício: tente cadastrar um veículo com ano de fabricação maior que o ano do
modelo e veja a mensagem de erro.

## Sessão 4 — CRUD nas views

Leia em `cars/views.py`:

- `vehicle_list_view`;
- `vehicle_create_view`;
- `vehicle_update_view`;
- `vehicle_delete_view`.

Observe o padrão:

1. receber a requisição;
2. validar o formulário;
3. salvar;
4. criar mensagem;
5. redirecionar.

Exercício: adicione um novo filtro por cor na listagem.

## Sessão 5 — regra de venda e transação

Volte ao model `Sale`, principalmente `clean()`, `save()` e `cancel()`.

O bloco `transaction.atomic()` garante que a venda e a alteração do estoque
sejam tratadas como uma única operação. Se uma parte falhar, o banco não fica
pela metade.

Exercício:

1. registre uma venda;
2. confira que o veículo mudou para vendido;
3. cancele;
4. confirme que voltou para disponível;
5. tente vender duas vezes e observe o bloqueio.

## Sessão 6 — agregações e dashboard

Leia `dashboard_view` em `cars/views.py`.

Procure por:

- `Count`;
- `Sum`;
- `Avg`;
- `TruncMonth`;
- `values()` e `annotate()`.

Essas operações correspondem a conceitos como `COUNT`, `SUM`, `AVG` e
`GROUP BY` no SQL.

Depois abra `CONSULTAS_SQL.sql` e compare as consultas SQL com o Django ORM.

## Sessão 7 — Pandas

Execute:

```powershell
py manage.py export_analytics
py analytics\analise_vendas.py
```

Leia `analytics/analise_vendas.py` e identifique:

- `read_csv()`;
- filtros com colunas;
- `merge()`;
- criação de coluna calculada;
- `groupby()`;
- `agg()`;
- `to_csv()`.

Exercício: gere uma tabela com ticket médio por forma de pagamento.

## Sessão 8 — testes

Execute:

```powershell
py manage.py test
```

Leia `cars/tests.py`. Cada teste segue a lógica:

1. preparar dados;
2. executar uma ação;
3. comparar o resultado esperado com o resultado real.

Exercício: crie um teste garantindo que o preço de compra não possa ser maior
que o preço anunciado.

## O que saber explicar em uma entrevista

- por que carro e moto foram unificados no model `Vehicle`;
- diferença entre `ForeignKey` e `ManyToManyField`;
- como uma venda atualiza o estoque;
- por que usamos `DecimalField` para dinheiro em vez de `FloatField`;
- como impedir uma venda duplicada;
- como calcular faturamento e lucro;
- diferença entre `SELECT`, `WHERE`, `JOIN`, `GROUP BY` e `HAVING`;
- como o Pandas recebe os dados do sistema;
- qual dificuldade apareceu e como você a resolveu.

Uma explicação curta do projeto:

> O projeto começou como um CRUD separado de carros e motos. Eu reorganizei a
> estrutura em um model único de veículo e acrescentei clientes, vendas, controle
> automático de estoque, relatórios SQL e análise com Pandas.
