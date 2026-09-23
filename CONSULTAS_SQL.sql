-- Consultas didáticas para executar no SQLite.
-- As tabelas foram criadas automaticamente pelos models do Django.

-- 1. Quantidade de veículos por status.
SELECT status, COUNT(*) AS quantidade
FROM cars_vehicle
GROUP BY status
ORDER BY quantidade DESC;

-- 2. Faturamento por mês (somente vendas confirmadas).
SELECT strftime('%Y-%m', sale_date) AS mes,
       COUNT(*) AS vendas,
       SUM(final_price) AS faturamento
FROM cars_sale
WHERE status = 'confirmed'
GROUP BY mes
ORDER BY mes;

-- 3. Ticket médio.
SELECT AVG(final_price) AS ticket_medio
FROM cars_sale
WHERE status = 'confirmed';

-- 4. Lucro bruto por venda.
SELECT s.id,
       b.name AS marca,
       v.model,
       v.purchase_price,
       s.final_price,
       s.final_price - v.purchase_price AS lucro_bruto
FROM cars_sale AS s
JOIN cars_vehicle AS v ON v.id = s.vehicle_id
JOIN cars_brands AS b ON b.id = v.brand_id
WHERE s.status = 'confirmed'
ORDER BY lucro_bruto DESC;

-- 5. Resultado por marca.
SELECT b.name AS marca,
       COUNT(s.id) AS vendas,
       SUM(s.final_price) AS faturamento,
       SUM(s.final_price - v.purchase_price) AS lucro_bruto
FROM cars_sale AS s
JOIN cars_vehicle AS v ON v.id = s.vehicle_id
JOIN cars_brands AS b ON b.id = v.brand_id
WHERE s.status = 'confirmed'
GROUP BY b.id, b.name
ORDER BY faturamento DESC;

-- 6. Clientes com mais compras.
SELECT c.name AS cliente,
       COUNT(s.id) AS compras,
       SUM(s.final_price) AS total_comprado
FROM cars_customer AS c
JOIN cars_sale AS s ON s.customer_id = c.id
WHERE s.status = 'confirmed'
GROUP BY c.id, c.name
ORDER BY compras DESC, total_comprado DESC;

-- 7. Veículos disponíveis há mais de 60 dias.
SELECT b.name AS marca,
       v.model,
       v.entry_date,
       CAST(julianday('now') - julianday(v.entry_date) AS INTEGER) AS dias_estoque
FROM cars_vehicle AS v
JOIN cars_brands AS b ON b.id = v.brand_id
WHERE v.status <> 'sold'
  AND julianday('now') - julianday(v.entry_date) > 60
ORDER BY dias_estoque DESC;

-- 8. Diferença entre preço anunciado e preço vendido.
SELECT b.name AS marca,
       v.model,
       v.asking_price,
       s.final_price,
       v.asking_price - s.final_price AS desconto
FROM cars_sale AS s
JOIN cars_vehicle AS v ON v.id = s.vehicle_id
JOIN cars_brands AS b ON b.id = v.brand_id
WHERE s.status = 'confirmed'
ORDER BY desconto DESC;

-- 9. Tempo médio entre entrada no estoque e venda.
SELECT AVG(julianday(s.sale_date) - julianday(v.entry_date)) AS media_dias_estoque
FROM cars_sale AS s
JOIN cars_vehicle AS v ON v.id = s.vehicle_id
WHERE s.status = 'confirmed';

-- 10. Valor do estoque disponível pelo preço de compra.
SELECT COUNT(*) AS veiculos,
       SUM(purchase_price) AS capital_em_estoque
FROM cars_vehicle
WHERE status IN ('available', 'reserved');
