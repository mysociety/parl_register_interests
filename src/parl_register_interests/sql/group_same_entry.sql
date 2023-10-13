-- We want to ensure we have the same name for all entries of the same person
-- But it's not like that in the source
-- So we get the last name declared, and then join that back to the original data
WITH LastMemberNames AS (
    SELECT DISTINCT public_whip_id, member_name
    FROM (
        SELECT DISTINCT
            public_whip_id,
            member_name,
            registry_date,
            ROW_NUMBER() OVER (PARTITION BY public_whip_id ORDER BY registry_date DESC) AS rn
        FROM {{ parquet_path }}
    ) as subquery
    WHERE rn = 1
) 

SELECT
    t.public_whip_id as public_whip_id,
    t.category_name as category_name,
    t.free_text as free_text,
    MIN(lm.member_name) AS member_name,
    MIN(t.registry_date) AS earliest_declaration,
    MAX(t.registry_date) AS latest_declaration
FROM {{ parquet_path }} t
JOIN LastMemberNames lm ON t.public_whip_id = lm.public_whip_id
GROUP BY
    t.public_whip_id,
    lm.member_name,
    t.category_name,
    t.free_text,
ORDER BY
    t.public_whip_id,
    latest_declaration,
    t.category_name,
    t.free_text,
    lm.member_name,
    earliest_declaration;
