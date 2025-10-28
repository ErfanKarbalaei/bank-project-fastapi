
SELECT
    date_trunc('hour', created_at) AS hour_utc,
    COUNT(*) AS success_count
FROM transactions
WHERE status = 'SUCCESS'
GROUP BY 1
ORDER BY 1;
