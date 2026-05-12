
-- Trigger 4: Pemeriksaan Status Klaim Missing Miles yang Duplikat

CREATE OR REPLACE FUNCTION fn_check_duplicate_missing_miles_claims()
RETURNS TRIGGER AS $$
DECLARE
    v_member_email TEXT;
BEGIN
    SELECT LOWER(au.email)
    INTO v_member_email
    FROM auth_system_member am
    JOIN auth_user au ON au.id = am.user_id
    WHERE am.id = NEW.member_id;

    IF EXISTS (
        SELECT 1
        FROM auth_system_claimmissingmiles c
        JOIN auth_system_member m ON m.id = c.member_id
        JOIN auth_user u ON u.id = m.user_id
        WHERE UPPER(c.flight_number) = UPPER(NEW.flight_number)
          AND c.flight_date = NEW.flight_date
          AND COALESCE(UPPER(c.ticket_number), '') = COALESCE(UPPER(NEW.ticket_number), '')
          AND LOWER(u.email) = v_member_email
          AND c.id != COALESCE(NEW.id, 0)
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

-- Trigger 2: Auto Update Member Tier Based on Total Miles

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

-- Trigger 3: Update Member Total Miles When Claim is Approved

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
