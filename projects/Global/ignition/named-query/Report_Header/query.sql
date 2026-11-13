SELECT 
    e.id AS equipment_id,
    e.equipment_name,
    u.unit_name,
    s.shift_name,
    k.kpi_name,
    t.target_value
FROM EQUIPMENT e
JOIN ORG_UNIT u ON e.unit_id = u.id
JOIN KPI_TARGET t ON t.unit_id = u.id
JOIN KPI_MASTER k ON k.id = t.kpi_id
JOIN SHIFT_MASTER s ON s.id = :shiftId
WHERE e.id = :equipmentId
