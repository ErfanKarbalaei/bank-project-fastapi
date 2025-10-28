
SELECT
    u.id AS user_id,
    u.full_name,
    date_trunc('month', t.created_at) AS month_utc,
    SUM(t.amount) AS total_amount,
    COUNT(*) AS tx_count
FROM transactions t
JOIN cards c ON c.id = t.source_card_id
JOIN users u ON u.id = c.user_id
WHERE t.status = 'SUCCESS'
GROUP BY u.id, u.full_name, date_trunc('month', t.created_at)
ORDER BY month_utc, u.id;
