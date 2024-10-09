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
    t.dup_count as dup_count,
    MIN(lm.member_name) AS member_name,
    MIN(t.registry_date) AS earliest_declaration,
    MAX(t.registry_date) AS latest_declaration,
    MAX(t.joined_source_order) AS source_order
FROM (
    SELECT *,
           year(CAST(registry_date as DATE)) * 100000 + month(CAST(registry_date as DATE)) * 1000 + day(CAST(registry_date as DATE)) * 100 + CAST(source_order AS INT) AS joined_source_order
    FROM {{ parquet_path }}
) t
JOIN LastMemberNames lm ON t.public_whip_id = lm.public_whip_id
GROUP BY
    t.public_whip_id,
    lm.member_name,
    t.category_name,
    t.free_text,
    t.dup_count
ORDER BY
    t.public_whip_id,
    latest_declaration,
    t.category_name,
    source_order,
    earliest_declaration;
