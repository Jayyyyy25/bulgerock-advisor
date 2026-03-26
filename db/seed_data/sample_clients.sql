-- Sample client data for development/testing

INSERT INTO clients (client_id, full_name, email, phone, risk_profile, advisor_id) VALUES
    ('CLI001', 'Alice Fontaine',    'alice.fontaine@email.com',    '+1-415-555-0101', 'aggressive',   'ADV01'),
    ('CLI002', 'Bernard Okafor',   'bernard.okafor@email.com',    '+1-212-555-0202', 'moderate',     'ADV01'),
    ('CLI003', 'Catherine Lim',    'catherine.lim@email.com',     '+1-310-555-0303', 'conservative', 'ADV02'),
    ('CLI004', 'David Mercer',     'david.mercer@email.com',      '+1-617-555-0404', 'aggressive',   'ADV02'),
    ('CLI005', 'Elena Vasquez',    'elena.vasquez@email.com',     '+1-305-555-0505', 'moderate',     'ADV01')
ON CONFLICT (client_id) DO NOTHING;

INSERT INTO policies (policy_id, client_id, policy_type, insurer, coverage_amount, premium, renewal_date, status) VALUES
    ('POL001', 'CLI001', 'Life',          'Prudential',  2000000, 3200, CURRENT_DATE + 5,  'active'),
    ('POL002', 'CLI001', 'Disability',    'MetLife',      500000, 1800, CURRENT_DATE + 45, 'active'),
    ('POL003', 'CLI002', 'Life',          'AIG',         1500000, 2400, CURRENT_DATE + 12, 'active'),
    ('POL004', 'CLI003', 'Long-Term Care','Mutual of Omaha', 800000, 4100, CURRENT_DATE + 3, 'active'),
    ('POL005', 'CLI004', 'Life',          'Prudential',  3000000, 5500, CURRENT_DATE + 60, 'active'),
    ('POL006', 'CLI005', 'Disability',    'Guardian',     750000, 2100, CURRENT_DATE + 8,  'active')
ON CONFLICT (policy_id) DO NOTHING;
