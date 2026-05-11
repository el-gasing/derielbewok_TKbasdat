-- ============================================================================
-- AeroMiles Database Triggers (PostgreSQL)
-- ============================================================================
-- These triggers implement business rules for the AeroMiles application
-- 
-- Triggers:
-- 1. TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS - Prevent duplicate missing miles claims
-- 2. TR_AUTO_UPDATE_MEMBER_TIER - Automatically update member tier based on total miles
--
-- Usage: Run this script on PostgreSQL database for online deployment
-- ============================================================================


-- ============================================================================
-- Trigger 1: Check for Duplicate Missing Miles Claims
-- ============================================================================
-- Purpose: Prevent duplicate missing miles claims with same flight details
-- Checks: Same member, flight_number, ticket_number, and flight_date
-- Status: Only checks against 'pending' and 'approved' claims
--
-- Error Message Format:
-- ERROR: Klaim untuk penerbangan \"<flight_number>\" pada tanggal \"<flight_date>\" 
--        dengan nomor tiket \"<ticket_number>\" sudah pernah diajukan sebelumnya.

CREATE OR REPLACE FUNCTION fn_check_duplicate_missing_miles_claims()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM auth_system_claimmissingmiles
        WHERE member_id = NEW.member_id
          AND UPPER(flight_number) = UPPER(NEW.flight_number)
          AND flight_date = NEW.flight_date
          AND (ticket_number IS NULL OR UPPER(ticket_number) = UPPER(NEW.ticket_number))
          AND status IN ('pending', 'approved')
          AND id != COALESCE(NEW.id, 0)
    ) THEN
        RAISE EXCEPTION 'ERROR: Klaim untuk penerbangan "%" pada tanggal "%" dengan nomor tiket "%" sudah pernah diajukan sebelumnya.',
            NEW.flight_number, NEW.flight_date, NEW.ticket_number;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS
BEFORE INSERT OR UPDATE ON auth_system_claimmissingmiles
FOR EACH ROW
EXECUTE FUNCTION fn_check_duplicate_missing_miles_claims();


-- ============================================================================
-- Trigger 2: Auto Update Member Tier Based on Total Miles
-- ============================================================================
-- Purpose: Automatically update member tier when total_miles changes
-- When: Triggered when claim is approved and miles are added to member
-- Tier Logic: Based on TIER table with minimal_tier_miles threshold
--
-- Flow:
-- 1. When claim approved -> miles added to member.total_miles
-- 2. This trigger checks if tier needs updating
-- 3. Sets appropriate tier based on minimal_tier_miles threshold

CREATE OR REPLACE FUNCTION fn_auto_update_member_tier()
RETURNS TRIGGER AS $$
DECLARE
    v_new_tier_id BIGINT;
BEGIN
    -- Only trigger when total_miles or award_miles changes
    IF (TG_OP = 'UPDATE' AND NEW.total_miles != OLD.total_miles) THEN
        -- Find appropriate tier based on new total_miles
        SELECT id INTO v_new_tier_id
        FROM auth_system_tier
        WHERE is_active = TRUE
          AND minimal_tier_miles <= NEW.total_miles
        ORDER BY minimal_tier_miles DESC
        LIMIT 1;
        
        -- Update tier if different from current
        IF v_new_tier_id != COALESCE(NEW.tier_id, 0) THEN
            NEW.tier_id = v_new_tier_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER TR_AUTO_UPDATE_MEMBER_TIER
BEFORE UPDATE ON auth_system_member
FOR EACH ROW
EXECUTE FUNCTION fn_auto_update_member_tier();


-- ============================================================================
-- Trigger 3: Update Member Total Miles When Claim is Approved
-- ============================================================================
-- Purpose: Automatically add miles to member when claim status changes to 'approved'
-- This ensures data consistency between claims and member total_miles

CREATE OR REPLACE FUNCTION fn_add_miles_on_claim_approval()
RETURNS TRIGGER AS $$
BEGIN
    -- When claim status changes to 'processed', add miles to member
    IF NEW.status = 'processed' AND OLD.status != 'processed' THEN
        UPDATE auth_system_member
        SET total_miles = total_miles + NEW.miles_amount,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.member_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER TR_ADD_MILES_ON_CLAIM_APPROVAL
AFTER UPDATE ON auth_system_claimmissingmiles
FOR EACH ROW
EXECUTE FUNCTION fn_add_miles_on_claim_approval();


-- ============================================================================
-- End of Triggers
-- ============================================================================
