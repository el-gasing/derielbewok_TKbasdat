-- ============================================================================
-- AeroMiles Stored Procedures (PostgreSQL)
-- ============================================================================
-- These stored procedures implement business logic for the AeroMiles application
-- 
-- Procedures:
-- 1. sp_check_duplicate_missing_miles_claim - Check for duplicate claims
-- 2. sp_get_member_tier - Get member's tier based on total miles
-- 3. sp_auto_update_member_tier - Auto-update member tier
-- 4. sp_process_claim_approval - Process claim approval with mile transfer
-- 5. sp_add_miles_to_member - Add miles to member
-- 6. sp_get_member_tier_info - Get detailed tier information for member
--
-- Usage: Run this script on PostgreSQL database for online deployment
-- ============================================================================


-- ============================================================================
-- Stored Procedure 1: Check Duplicate Missing Miles Claim
-- ============================================================================
-- Purpose: Check if a duplicate missing miles claim exists
-- Parameters:
--   p_member_id - Member ID
--   p_email_member - Email member
--   p_flight_number - Flight number
--   p_ticket_number - Ticket number (optional)
--   p_flight_date - Flight date
-- Returns:
--   r_duplicate_claim_id - ID of duplicate claim if exists, NULL otherwise

CREATE OR REPLACE FUNCTION sp_check_duplicate_missing_miles_claim(
    p_member_id BIGINT,
        p_email_member VARCHAR,
    p_flight_number VARCHAR,
    p_ticket_number VARCHAR,
    p_flight_date DATE
)
RETURNS BIGINT AS $$
DECLARE
    v_claim_id BIGINT;
BEGIN
    SELECT id INTO v_claim_id
        FROM auth_system_claimmissingmiles c
        JOIN auth_system_member m ON m.id = c.member_id
        JOIN auth_user u ON u.id = m.user_id
        WHERE LOWER(u.email) = LOWER(p_email_member)
            AND UPPER(c.flight_number) = UPPER(p_flight_number)
            AND c.flight_date = p_flight_date
            AND COALESCE(UPPER(c.ticket_number), '') = COALESCE(UPPER(p_ticket_number), '')
    LIMIT 1;
    
    RETURN v_claim_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Stored Procedure 2: Get Member Tier
-- ============================================================================
-- Purpose: Get appropriate tier for a given total miles
-- Parameters:
--   p_total_miles - Total miles amount
-- Returns:
--   r_tier_id - ID of appropriate tier, NULL if no tier matches

CREATE OR REPLACE FUNCTION sp_get_member_tier(p_total_miles BIGINT)
RETURNS BIGINT AS $$
DECLARE
    v_tier_id BIGINT;
BEGIN
    SELECT id INTO v_tier_id
    FROM auth_system_tier
    WHERE is_active = TRUE
      AND minimal_tier_miles <= p_total_miles
    ORDER BY minimal_tier_miles DESC
    LIMIT 1;
    
    RETURN v_tier_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Stored Procedure 3: Auto Update Member Tier
-- ============================================================================
-- Purpose: Automatically update member's tier based on total_miles
-- Parameters:
--   p_member_id - Member ID
-- Returns:
--   r_success - TRUE if tier was updated, FALSE otherwise

CREATE OR REPLACE FUNCTION sp_auto_update_member_tier(p_member_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_member_total_miles BIGINT;
    v_new_tier_id BIGINT;
    v_current_tier_id BIGINT;
BEGIN
    -- Get member's current total miles and tier
    SELECT total_miles, tier_id INTO v_member_total_miles, v_current_tier_id
    FROM auth_system_member
    WHERE id = p_member_id;
    
    -- Check if member exists
    IF v_member_total_miles IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Get appropriate tier based on total miles
    v_new_tier_id := sp_get_member_tier(v_member_total_miles);
    
    -- Update tier if different
    IF v_new_tier_id != COALESCE(v_current_tier_id, 0) THEN
        UPDATE auth_system_member
        SET tier_id = v_new_tier_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = p_member_id;
        
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Stored Procedure 4: Process Claim Approval
-- ============================================================================
-- Purpose: Process claim approval - add miles to member and update tier
-- Parameters:
--   p_claim_id - Claim ID to process
--   p_staff_id - Staff ID approving the claim
-- Returns:
--   r_success - TRUE if successfully processed, FALSE otherwise

CREATE OR REPLACE FUNCTION sp_process_claim_approval(
    p_claim_id BIGINT,
    p_staff_id BIGINT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_member_id BIGINT;
    v_miles_amount BIGINT;
    v_current_status VARCHAR;
BEGIN
    -- Get claim details
    SELECT member_id, miles_amount, status INTO v_member_id, v_miles_amount, v_current_status
    FROM auth_system_claimmissingmiles
    WHERE id = p_claim_id;
    
    -- Check if claim exists and not already processed
    IF v_current_status = 'processed' THEN
        RETURN FALSE;
    END IF;
    
    -- Update claim status to processed
    UPDATE auth_system_claimmissingmiles
    SET status = 'processed',
        approved_by_id = p_staff_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_claim_id;
    
    -- Add miles to member
    PERFORM sp_add_miles_to_member(v_member_id, v_miles_amount);
    
    -- Auto-update member tier
    PERFORM sp_auto_update_member_tier(v_member_id);
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Stored Procedure 5: Add Miles to Member
-- ============================================================================
-- Purpose: Add miles to member's total_miles
-- Parameters:
--   p_member_id - Member ID
--   p_miles_amount - Amount of miles to add
-- Returns:
--   r_new_total_miles - New total miles for member

CREATE OR REPLACE FUNCTION sp_add_miles_to_member(
    p_member_id BIGINT,
    p_miles_amount BIGINT
)
RETURNS BIGINT AS $$
DECLARE
    v_new_total BIGINT;
BEGIN
    -- Add miles to member
    UPDATE auth_system_member
    SET total_miles = total_miles + p_miles_amount,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_member_id
    RETURNING total_miles INTO v_new_total;
    
    RETURN v_new_total;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Stored Procedure 6: Get Member Tier Info
-- ============================================================================
-- Purpose: Get comprehensive tier information for a member
-- Parameters:
--   p_member_id - Member ID
-- Returns:
--   Table with columns:
--   - member_id - Member ID
--   - member_name - Member full name
--   - total_miles - Member's total miles
--   - current_tier - Current tier name
--   - current_tier_id - Current tier ID
--   - next_tier - Next achievable tier name
--   - next_tier_id - Next tier ID
--   - miles_to_next_tier - Miles needed to reach next tier

CREATE OR REPLACE FUNCTION sp_get_member_tier_info(p_member_id BIGINT)
RETURNS TABLE (
    member_id BIGINT,
    member_name VARCHAR,
    total_miles BIGINT,
    current_tier VARCHAR,
    current_tier_id BIGINT,
    next_tier VARCHAR,
    next_tier_id BIGINT,
    miles_to_next_tier BIGINT
) AS $$
DECLARE
    v_total_miles BIGINT;
    v_current_tier_id BIGINT;
    v_next_tier_minimal BIGINT;
    v_next_tier_id BIGINT;
BEGIN
    -- Get member's total miles and current tier
    SELECT m.total_miles, m.tier_id
    INTO v_total_miles, v_current_tier_id
    FROM auth_system_member m
    WHERE m.id = p_member_id;
    
    -- Get next tier
    SELECT id, minimal_tier_miles
    INTO v_next_tier_id, v_next_tier_minimal
    FROM auth_system_tier
    WHERE is_active = TRUE
      AND minimal_tier_miles > v_total_miles
    ORDER BY minimal_tier_miles ASC
    LIMIT 1;
    
    -- Return result
    RETURN QUERY
    SELECT
        p_member_id,
        CONCAT(u.first_name, ' ', u.last_name),
        v_total_miles,
        COALESCE(ct.tier_name, 'None'),
        v_current_tier_id,
        COALESCE(nt.tier_name, 'N/A'),
        v_next_tier_id,
        CASE WHEN v_next_tier_id IS NOT NULL
            THEN v_next_tier_minimal - v_total_miles
            ELSE 0
        END
    FROM auth_system_member m
    JOIN auth_system_user u ON m.user_id = u.id
    LEFT JOIN auth_system_tier ct ON m.tier_id = ct.id
    LEFT JOIN auth_system_tier nt ON nt.id = v_next_tier_id
    WHERE m.id = p_member_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- End of Stored Procedures
-- ============================================================================
