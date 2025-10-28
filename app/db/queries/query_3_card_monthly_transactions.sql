
SELECT
    c.id AS card_id,
    c.card_number,
    date_trunc('month', t.created_at) AS month_utc,
    SUM(t.amount) AS total_amount,
    COUNT(*) AS tx_count
FROM transactions t
JOIN cards c ON c.id = t.source_card_id
WHERE t.status = 'SUCCESS'
GROUP BY c.id, c.card_number, date_trunc('month', t.created_at)
ORDER BY month_utc, c.id;
