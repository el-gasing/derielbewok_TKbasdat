-- ============================================================================
-- AeroMiles Tier Configuration (PostgreSQL/SQLite)
-- ============================================================================
-- Initial data for Tier table
-- This script populates the tier system with default tier levels
--
-- Tier Levels:
-- 1. Bronze - Starting tier (0 miles)
-- 2. Silver - Mid tier (10,000 miles)
-- 3. Gold - High tier (25,000 miles)
-- 4. Platinum - Premium tier (50,000 miles)
--
-- Usage: Run this script to initialize the tier system
-- ============================================================================

-- Delete existing tiers (optional, comment out if updating)
-- DELETE FROM auth_system_tier;

-- Insert tier levels
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

-- ============================================================================
-- Optional: Update existing member tiers based on their miles
-- Uncomment this section to auto-assign tiers to existing members
-- ============================================================================

-- UPDATE auth_system_member m
-- SET tier_id = (
--     SELECT id FROM auth_system_tier t
--     WHERE t.is_active = TRUE
--       AND t.minimal_tier_miles <= m.total_miles
--     ORDER BY t.minimal_tier_miles DESC
--     LIMIT 1
-- ),
-- updated_at = CURRENT_TIMESTAMP
-- WHERE tier_id IS NULL OR tier_id NOT IN (
--     SELECT id FROM auth_system_tier WHERE is_active = TRUE
--       AND minimal_tier_miles <= m.total_miles
--     ORDER BY minimal_tier_miles DESC
--     LIMIT 1
-- );

-- ============================================================================
-- End of Tier Configuration
-- ============================================================================
