SELECT 
    id,
    reference_number,
    event_date,
    line_number,
    category,
    due_date,
    issue,
    action,
    person_responsible,
    status
FROM issues_log
WHERE 
    (:line IS NULL OR :line = '' OR line_number = :line)
AND 
    (:category IS NULL OR :category = '' OR category = :category)
AND 
	(:status IS NULL OR :status = '' OR status = :status)
ORDER BY id DESC