SELECT application_id, 
       coalesce(income_reported, '0') as income_str, 
       requested_amount, 
       coalesce(credit_score, 'N/A') as credit_score
FROM ext_application_source
-- [Governance Agent]
SELECT application_id, 
       coalesce(income_reported, 'UNKNOWN') as income_str, 
       requested_amount, 
       coalesce(credit_score, 'N/A') as credit_score
FROM ext_application_source