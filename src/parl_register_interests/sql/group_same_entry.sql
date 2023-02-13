select
    public_whip_id,
    category_name,
    free_text,
    last(member_name) as member_name,
    min(registry_date) as earliest_declaration,
    max(registry_date) as latest_declaration
from {{ parquet_path }}
group by public_whip_id, category_name, free_text
order by public_whip_id, latest_declaration