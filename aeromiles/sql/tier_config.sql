
INSERT INTO auth_system_tier (tier_name, minimal_tier_miles, minimal_frekuensi_terbang, is_active, created_at, updated_at)
VALUES
    -- Bronze Tier (Entry level)
    ('bronze', 0, 1, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Silver Tier (Frequent flyer)
    ('silver', 10000, 5, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Gold Tier (Very frequent flyer)
    ('gold', 25000, 10, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Platinum Tier (Elite member)
    ('platinum', 50000, 20, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (tier_name) DO NOTHING;
